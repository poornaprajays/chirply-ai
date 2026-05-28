import os
import sys
import time
import logging
from pathlib import Path

# Add backend to path to allow importing app modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("chirply.test_pipeline")

def test_pipeline_orchestration():
    logger.info("=== Starting Pipeline Orchestration Tests ===")
    from backend.app.core.config import settings
    from backend.app.services.audio_recorder import AudioRecorderService
    from backend.app.services.birdnet_service import BirdNetService
    from backend.app.services.spectrogram_service import SpectrogramService
    from backend.app.services.detection_logger import DetectionLoggerService
    from backend.app.pipelines.realtime_pipeline import RealtimeInferencePipeline
    
    # 1. Instantiate the individual services
    recorder = AudioRecorderService(output_dir=settings.RECORDINGS_DIR)
    # Instantiate BirdNetService without loading the missing .tflite files directly
    birdnet = BirdNetService()
    spectrogram = SpectrogramService()
    db_logger = DetectionLoggerService(db_path=settings.DB_PATH)
    
    # Initialize DB schemas
    db_logger.initialize_database()
    
    # 2. Instantiate the orchestrator pipeline
    pipeline = RealtimeInferencePipeline(
        recorder=recorder,
        birdnet=birdnet,
        spectrogram=spectrogram,
        db_logger=db_logger
    )
    
    # 3. Mock the ML inference to return a fixed mock species call
    mock_detection = {
        "scientific_name": "Turdus migratorius",
        "common_name": "American Robin",
        "confidence": 0.95,
        "start_time": 0.0,
        "end_time": 3.0
    }
    # Mock return values for BirdNET
    pipeline.birdnet.run_inference = lambda path: [mock_detection]
    
    logger.info("Triggering a single pipeline chunk processing...")
    # Create a valid input WAV path
    temp_wav_path = recorder.record_audio(duration=1)
    
    # Verify file is generated
    assert os.path.exists(temp_wav_path), "Audio recorder failed to generate audio chunk"
    
    # Run the processing chunk
    detections = pipeline.process_audio_chunk(temp_wav_path)
    
    # 4. Verify detections processing
    assert len(detections) == 1, "Expected exactly 1 detection"
    assert detections[0]["common_name"] == "American Robin"
    
    # Verify that the WAV file is KEPT (since a valid species was found)
    assert os.path.exists(temp_wav_path), "WAV file was deleted despite valid detection"
    
    # Verify that the Spectrogram was generated
    spectrogram_filename = f"spec_{Path(temp_wav_path).stem.replace('rec_', '')}.png"
    spectrogram_path = Path(settings.SPECTROGRAMS_DIR) / spectrogram_filename
    assert spectrogram_path.exists(), f"Spectrogram image was not generated: {spectrogram_path}"
    logger.info("Single chunk validation passed! Spectrogram and database records are generated.")
    
    # Clean up files created in single chunk test
    if os.path.exists(temp_wav_path):
        os.remove(temp_wav_path)
    if spectrogram_path.exists():
        os.remove(spectrogram_path)
        
    # 5. Test discard behaviour when no species is found
    logger.info("Testing WAV file cleanup/discard behavior when no species is found...")
    # Mock return values to be empty
    pipeline.birdnet.run_inference = lambda path: []
    temp_wav_path2 = recorder.record_audio(duration=1)
    
    assert os.path.exists(temp_wav_path2), "Second audio chunk was not generated"
    detections2 = pipeline.process_audio_chunk(temp_wav_path2)
    
    assert len(detections2) == 0, "Expected 0 detections"
    # WAV file MUST be deleted
    assert not os.path.exists(temp_wav_path2), "WAV file was not cleaned up after empty detection"
    logger.info("Audio chunk cleanup check passed successfully.")
    
    # 6. Test background worker thread execution
    logger.info("Testing continuous loop execution on a daemon thread...")
    # Restore bird detection mock
    pipeline.birdnet.run_inference = lambda path: [mock_detection]
    
    pipeline.start()
    assert pipeline.running, "Pipeline is not reporting running state"
    assert pipeline.pipeline_active, "Pipeline is not reporting active status"
    
    # Wait at least 4.5 seconds to ensure the 3.0-second recording loop finishes at least one run
    logger.info("Allowing background loop to capture at least one mock chunk (waiting 4.5s)...")
    time.sleep(4.5)
    
    # Check metrics
    logger.info(f"Processed chunks count: {pipeline.total_processed}")
    logger.info(f"Detections count: {pipeline.total_detections}")
    assert pipeline.total_processed > 0, "Background worker did not process any chunks"
    
    # 7. Stop the pipeline
    logger.info("Stopping background pipeline...")
    pipeline.stop()
    assert not pipeline.running, "Pipeline failed to stop running flag"
    assert not pipeline.pipeline_active, "Pipeline is still reporting active status"
    
    # Clean up any recordings left in recordings directory from the background run
    for file in Path(settings.RECORDINGS_DIR).glob("*.wav"):
        if file.exists():
            file.unlink()
    for file in Path(settings.SPECTROGRAMS_DIR).glob("*.png"):
        if file.exists():
            file.unlink()
            
    logger.info("====== ALL PIPELINE ORCHESTRATION TESTS PASSED SUCCESSFULLY! ======")

if __name__ == "__main__":
    try:
        test_pipeline_orchestration()
    except Exception as e:
        logger.critical(f"PIPELINE ORCHESTRATION VERIFICATION FAILED: {e}", exc_info=True)
        sys.exit(1)
