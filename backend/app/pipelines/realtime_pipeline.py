import logging
import os
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from backend.app.core.config import settings
from backend.app.services.audio_recorder import AudioRecorderService
from backend.app.services.birdnet_service import BirdNetService
from backend.app.services.spectrogram_service import SpectrogramService
from backend.app.services.detection_logger import DetectionLoggerService

logger = logging.getLogger("chirply.pipeline")

class RealtimeInferencePipeline:
    """
    Background worker orchestrator. Manages continuous capture loop:
    Audio Ingestion -> ML Inference Classify -> Spectrogram Image Generation -> SQL Commits.
    
    Why Orchestration Remains Separate from Service Internals:
    1. Single Responsibility Principle (SRP): Service classes focus on execution mechanics (ALSA calls,
       tensor operations, PNG rendering, SQLite schema). The pipeline focuses purely on time-sequencing,
       thread boundaries, error recovery, and data flow.
    2. Modularity & Parallel Dev: Service APIs remain clean. They can be tested independently and
       replaced (e.g. swapping ALSA arecord for pyaudio) without touching the orchestration engine.
    3. Scalability: The pipeline acts as a decoupled controller. This makes it trivial to expand:
       - REST polling: FastAPI routes can query the database written by this pipeline without blocking the pipeline.
       - WebSocket upgrades: A socket client wrapper can tap into pipeline hooks/callbacks to broadcast live.
       - Multi-device scaling: We can run multiple pipeline instances targeting different USB ports/ReSpeakers.
       - Uploaded-audio analysis: An offline processor can instantiate the services to parse pre-recorded audio chunks.
    """
    
    def __init__(self, recorder: AudioRecorderService, birdnet: BirdNetService, 
                 spectrogram: SpectrogramService, db_logger: DetectionLoggerService):
        """
        Binds operational services and initializes status parameters.
        """
        self.recorder = recorder
        self.birdnet = birdnet
        self.spectrogram = spectrogram
        self.db_logger = db_logger
        
        self.running = False
        self.pipeline_active = False
        self.worker_thread = None
        
        # Telemetry metrics
        self.last_run_timestamp = None
        self.total_processed = 0
        self.total_detections = 0
        
        # Track last hourly cleanup execution
        self.last_cleanup_time = time.time()
        
        logger.info("RealtimeInferencePipeline initialized successfully.")

    def start(self) -> None:
        """
        Launches non-blocking background consumer threads.
        """
        if self.running or (self.worker_thread and self.worker_thread.is_alive()):
            logger.warning("Pipeline is already running.")
            return

        logger.info("Starting RealtimeInferencePipeline background worker...")
        self.running = True
        self.pipeline_active = True
        
        # Spawn loop inside a daemon thread so it exits when the main thread shuts down
        self.worker_thread = threading.Thread(target=self.run_loop, name="chirply_worker", daemon=True)
        self.worker_thread.start()
        logger.info("Pipeline worker thread started successfully.")

    def stop(self) -> None:
        """
        Triggers loop shutdown, joins the worker thread, and shuts down operational state.
        """
        if not self.running:
            logger.warning("Pipeline is not currently active.")
            return

        logger.info("Stopping RealtimeInferencePipeline...")
        self.running = False
        self.pipeline_active = False
        
        if self.worker_thread:
            logger.info("Waiting for pipeline worker thread to join...")
            self.worker_thread.join(timeout=5.0)
            if self.worker_thread.is_alive():
                logger.warning("Worker thread did not stop within timeout. Forcing shutdown.")
            else:
                logger.info("Worker thread joined cleanly.")
            self.worker_thread = None
            
        logger.info("Pipeline stopped successfully.")

    def run_loop(self) -> None:
        """
        Main worker execution loop running in a dedicated thread.
        Continuous execution steps:
        1. Capture raw audio block via recorder
        2. Run BirdNET inference checks
        3. If species detected above threshold, generate spectrogram PNG
        4. Log results to SQLite DB volume
        5. Clean up temporary files (WAV) if no species is found
        6. Periodically rotate and prune old database / spectrogram logs
        """
        logger.info("Entering continuous ecoacoustic processing loop...")
        
        # Loop safety configuration
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            audio_path = None
            try:
                self.last_run_timestamp = datetime.utcnow().isoformat() + "Z"
                
                # 1. Capture raw audio segment (typically 3 seconds)
                # Note: AudioRecorderService blocks for the duration of the capture (e.g. 3s),
                # which acts as the natural clock/timer regulating the loop pacing.
                audio_path = self.recorder.record_audio(duration=int(settings.AUDIO_CHUNK_DURATION_SECONDS))
                
                if not audio_path or not os.path.exists(audio_path):
                    raise RuntimeError("Audio recorder returned an invalid file path.")
                
                # 2. Process the audio segment
                self.process_audio_chunk(audio_path)
                
                # Reset consecutive error counter on successful iteration
                consecutive_errors = 0
                self.total_processed += 1
                
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt detected. Gracefully exiting loop.")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in realtime pipeline iteration: {e}", exc_info=True)
                consecutive_errors += 1
                
                # If we encounter persistent recording failures (e.g. unplugged ReSpeaker),
                # slow down the loop to avoid CPU spin locks.
                sleep_time = min(5 * consecutive_errors, 30)
                logger.info(f"Cooling down pipeline for {sleep_time}s due to errors...")
                time.sleep(sleep_time)
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical("Maximum consecutive pipeline failures reached. Pausing loop operations.")
                    self.pipeline_active = False
            
            # 3. Perform hourly cleanup tasks
            current_time = time.time()
            if current_time - self.last_cleanup_time > 3600:
                try:
                    logger.info("Running periodic edge database and storage audits...")
                    # Prune old spectrogram images
                    self.spectrogram.cleanup_old_spectrograms(max_age_hours=24)
                    
                    # Prune old recordings WAV files using setting threshold
                    from backend.app.utils.file_utils import FileUtils
                    FileUtils.cleanup_old_files(settings.RECORDINGS_DIR, max_files=1000)
                    
                    self.last_cleanup_time = current_time
                except Exception as e:
                    logger.error(f"Failed to execute periodic cleanup tasks: {e}", exc_info=True)

        logger.info("Continuous processing loop terminated.")
        self.pipeline_active = False

    def process_audio_chunk(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Executes model inference, draws spectrograms, and saves valid events to SQLite.
        If no birds are detected or confidence is low, deletes the audio chunk to save space.
        """
        logger.info(f"Pipeline processing audio chunk: {Path(audio_path).name}")
        detections = []
        keep_audio = False
        
        try:
            # 1. Run inference
            # BirdNetService uses settings.MIN_CONFIDENCE_THRESHOLD by default
            detections = self.birdnet.run_inference(audio_path)
            
            # 2. Evaluate results
            if len(detections) > 0:
                logger.info(f"BirdNET detected {len(detections)} candidate species above confidence.")
                keep_audio = True  # We want to preserve the WAV clip for user playback
                
                # 3. Generate visual spectrogram for this chunk
                spectrogram_path = ""
                try:
                    spectrogram_path = self.spectrogram.generate_spectrogram(audio_path)
                except Exception as spec_err:
                    logger.error(f"Spectrogram rendering failed during pipeline run: {spec_err}")
                
                # 4. Log each detection event to SQLite
                for det in detections:
                    try:
                        det_id = self.db_logger.log_detection(
                            scientific_name=det["scientific_name"],
                            common_name=det["common_name"],
                            confidence=det["confidence"],
                            audio_file=os.path.basename(audio_path),
                            spectrogram_file=os.path.basename(spectrogram_path) if spectrogram_path else "",
                            start_time=det.get("start_time", 0.0),
                            end_time=det.get("end_time", 3.0)
                        )
                        self.total_detections += 1
                        logger.info(f"Recorded detection: {det['common_name']} -> {det_id}")
                    except Exception as db_err:
                        logger.error(f"Failed to write detection to database: {db_err}")
            else:
                logger.info(f"No species detected in chunk: {Path(audio_path).name}. Discarding.")
                
        except Exception as e:
            logger.error(f"Failed to process audio segment: {e}", exc_info=True)
            
        finally:
            # 5. Clean up temporary WAV file if it contains no valid detections
            if not keep_audio and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    logger.debug(f"Temporary audio clip successfully purged: {Path(audio_path).name}")
                except OSError as e:
                    logger.error(f"Failed to delete temporary audio clip {audio_path}: {e}")
                    
        return detections

# Backward compatibility alias
RealtimePipeline = RealtimeInferencePipeline
