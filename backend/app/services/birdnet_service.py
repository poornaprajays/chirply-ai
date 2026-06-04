import os
import wave
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from backend.app.core.config import settings

# Edge Optimization: Prefer tflite_runtime on Raspberry Pi to avoid installing
# the full 500MB+ TensorFlow package, saving hundreds of megabytes of RAM.
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    try:
        import tensorflow.lite as tflite
    except ImportError:
        tflite = None

logger = logging.getLogger("chirply.services.birdnet")

class BirdNetService:
    """
    Edge-optimized inference wrapper for the BirdNET TFLite acoustic classifier.
    Designed to run efficiently on memory-constrained devices like the Raspberry Pi.
    """
    
    def __init__(self, model_path: Optional[str] = None, 
                 labels_path: Optional[str] = None,
                 default_confidence: Optional[float] = None):
        """
        Sets model paths, labels paths, and default configurations.
        Defaults are consumed from global application settings.
        """
        self.model_path = os.path.abspath(model_path or settings.BIRDNET_MODEL_PATH)
        self.labels_path = os.path.abspath(labels_path or settings.BIRDNET_LABELS_PATH)
        self.default_confidence = default_confidence if default_confidence is not None else settings.MIN_CONFIDENCE_THRESHOLD
        
        self.interpreter = None
        self.labels = []
        self.input_index = None
        self.output_index = None
        self.input_sample_size = None

        # Check if we should fall back to developer mock mode
        self.mock_mode = False
        if tflite is None or not os.path.exists(self.model_path) or not os.path.exists(self.labels_path):
            self.mock_mode = True
            logger.warning("BirdNetService running in DEVELOPER MOCK MODE because TFLite is unavailable or model files are missing.")

    def load_model(self) -> None:
        """
        Loads the TFLite interpreter and pre-allocates memory tensors exactly once.
        Also parses labels.txt for fast taxonomical name mappings.
        
        Raspberry Pi Friendly Design:
        - One-time allocation: prevents memory fragmentation and reduces inference-to-inference CPU cycles.
        """
        if self.mock_mode:
            logger.info("Initializing mock labels for Developer Mock Mode...")
            self.labels = [
                "Cyanocitta cristata (Blue Jay)",
                "Cardinalis cardinalis (Northern Cardinal)",
                "Turdus migratorius (American Robin)",
                "Melospiza melodia (Song Sparrow)",
                "Passer domesticus (House Sparrow)"
            ]
            self.input_sample_size = 144000
            return

        if tflite is None:
            err_msg = "Neither tflite_runtime nor tensorflow.lite was found. Please install tflite-runtime."
            logger.critical(err_msg)
            raise ImportError(err_msg)
            
        logger.info("Initializing and pre-loading BirdNET TFLite model...")
        
        # Verify filesystem paths exist before loading
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"BirdNET model file not found at: {self.model_path}")
        if not os.path.exists(self.labels_path):
            raise FileNotFoundError(f"BirdNET labels file not found at: {self.labels_path}")

        try:
            # Initialize the interpreter
            self.interpreter = tflite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            
            # Fetch tensor input/output structures
            input_details = self.interpreter.get_input_details()
            output_details = self.interpreter.get_output_details()
            
            self.input_index = input_details[0]["index"]
            self.output_index = output_details[0]["index"]
            
            # Record input sample size (Typically 144000 samples for 3s of 48kHz audio)
            self.input_sample_size = input_details[0]["shape"][1]
            logger.info(f"BirdNET model loaded. Expected input sample size: {self.input_sample_size}")
            
            # Parse species classes labels
            with open(self.labels_path, "r", encoding="utf-8") as f:
                self.labels = [line.strip() for line in f.readlines() if line.strip()]
            logger.info(f"Loaded {len(self.labels)} species labels from taxonomy index.")
            
        except Exception as e:
            logger.error(f"Failed to load BirdNET model interpreter: {e}", exc_info=True)
            raise

    def parse_detection(self, label_index: int, confidence: float) -> Dict[str, Any]:
        """
        Normalizes raw model prediction indexes and probabilities into standardized JSON formats.
        
        Raspberry Pi Friendly Design:
        - Avoids compiling regex structures; relies on optimized string partitions.
        - Outputs standard dictionaries ready for immediate database inserts and API delivery.
        """
        if label_index >= len(self.labels):
            return {
                "scientific_name": "Unknown",
                "common_name": "Unknown",
                "confidence": float(confidence),
                "start_time": 0.0,
                "end_time": 3.0
            }
            
        label = self.labels[label_index]
        
        # BirdNET labels standard format: "0001_Cyanocitta cristata_Blue Jay" or "Cyanocitta cristata (Blue Jay)"
        scientific_name = "Unknown"
        common_name = "Unknown"
        
        # Clean leading digits prefix if present (e.g. '0001_')
        clean_label = label
        if "_" in label:
            parts = label.split("_", 1)
            if parts[0].isdigit():
                clean_label = parts[1]
                
        # Split Scientific and Common classifications
        if "(" in clean_label and ")" in clean_label:
            # Format: Scientific Name (Common Name)
            sci, com = clean_label.split("(", 1)
            scientific_name = sci.strip()
            common_name = com.replace(")", "").strip()
        elif "_" in clean_label:
            # Format: Scientific_Name_Common_Name or Scientific Name_Common Name
            parts = clean_label.split("_")
            scientific_name = parts[0].strip()
            common_name = parts[1].strip() if len(parts) > 1 else scientific_name
        else:
            scientific_name = clean_label.strip()
            common_name = clean_label.strip()
            
        return {
            "scientific_name": scientific_name,
            "common_name": common_name,
            "confidence": float(confidence),
            "start_time": 0.0,
            "end_time": 3.0
        }

    def filter_detections(self, detections: List[Dict[str, Any]], 
                          min_confidence: float) -> List[Dict[str, Any]]:
        """
        Prunes candidate identifications that fall below the confidence barrier.
        """
        return [det for det in detections if det["confidence"] >= min_confidence]

    def run_inference(self, audio_path: str, 
                       min_confidence: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Executes model inference on a target WAV file chunk.
        
        Raspberry Pi Friendly Design:
        - Uses native wave library decoding to keep memory footprints tiny.
        - Automatically rescales and pads audio segments without heavy math transformations.
        """
        if self.interpreter is None and not self.mock_mode:
            self.load_model()
            
        threshold = min_confidence if min_confidence is not None else self.default_confidence
        
        if self.mock_mode:
            if not self.labels:
                self.load_model()
            import random
            import time
            # 10% chance of no detection
            if random.random() < 0.1:
                return []
            num_dets = random.choice([1, 2])
            detections = []
            species_pool = [
                ("Cyanocitta cristata", "Blue Jay"),
                ("Cardinalis cardinalis", "Northern Cardinal"),
                ("Turdus migratorius", "American Robin"),
                ("Melospiza melodia", "Song Sparrow"),
                ("Passer domesticus", "House Sparrow")
            ]
            selected = random.sample(species_pool, num_dets)
            for sci, com in selected:
                detections.append({
                    "scientific_name": sci,
                    "common_name": com,
                    "confidence": round(random.uniform(0.72, 0.98), 2),
                    "start_time": 0.0,
                    "end_time": 3.0
                })
            detections.sort(key=lambda x: x["confidence"], reverse=True)
            time.sleep(0.1) # Simulate brief inference latency
            logger.info(f"BirdNET mock inference complete. Identified {len(detections)} mock species.")
            return detections

        # Verify file path exists
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found for inference: {audio_path}")
            return []
            
        try:
            # Decode audio using pure Python wave module
            with wave.open(audio_path, "rb") as w:
                params = w.getparams()
                frames = w.readframes(params.nframes)
                
                # Convert buffer to float32 (Normalized PCM -1.0 to 1.0)
                audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Convert stereo to mono by indexing step channel if needed
                if params.nchannels > 1:
                    audio_data = audio_data[::params.nchannels]
                    
            # Auto pad or crop buffer array to match interpreter expectations
            if len(audio_data) < self.input_sample_size:
                audio_data = np.pad(audio_data, (0, self.input_sample_size - len(audio_data)), mode="constant")
            elif len(audio_data) > self.input_sample_size:
                audio_data = audio_data[:self.input_sample_size]
                
            # Create a 2D batch tensor input container [1, input_size]
            input_tensor = np.array([audio_data], dtype=np.float32)
            
            # Pass data and trigger TFLite prediction calculations
            self.interpreter.set_tensor(self.input_index, input_tensor)
            self.interpreter.invoke()
            
            # Fetch raw output predictions
            raw_predictions = self.interpreter.get_tensor(self.output_index)[0]
            
            # Filter and parse detections
            detections = []
            for i, probability in enumerate(raw_predictions):
                if probability >= threshold:
                    parsed_det = self.parse_detection(i, probability)
                    detections.append(parsed_det)
                    
            # Sort results descending by confidence
            detections.sort(key=lambda x: x["confidence"], reverse=True)
            logger.info(f"BirdNET inference complete. Identified {len(detections)} candidate species.")
            return detections
            
        except Exception as e:
            logger.error(f"Error executing BirdNET TFLite inference: {e}", exc_info=True)
            return []

