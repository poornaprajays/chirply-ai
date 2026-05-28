import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

# Resolve project base directory dynamically relative to this config file.
# config.py is at backend/app/core/config.py, so parents[3] resolves to the project root directory.
BASE_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    """
    Global application settings for chirply-ai.
    Enforces clean environment configurations with edge-optimized defaults.
    """
    # Base Application Metadata
    APP_NAME: str = "Chirply AI"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"
    
    # SQLite Database Config
    DB_PATH: str = str(BASE_DIR / "data" / "detections" / "chirply.db")
    
    # Audio Ingestion & ReSpeaker Configuration
    AUDIO_SAMPLE_RATE: int = 16000          # 16kHz mono is BirdNET standard
    AUDIO_CHANNELS: int = 1                 # Mono recording
    AUDIO_CHUNK_DURATION_SECONDS: float = 3.0 # BirdNET processes 3-second audio windows
    AUDIO_INPUT_INDEX: int = 1              # Hardware ALSA interface index for ReSpeaker
    
    # Inference Thresholds
    BIRDNET_MODEL_PATH: str = str(BASE_DIR / "backend" / "models" / "model.tflite")
    BIRDNET_LABELS_PATH: str = str(BASE_DIR / "backend" / "models" / "labels.txt")
    MIN_CONFIDENCE_THRESHOLD: float = 0.70  # Default species identification threshold
    DEFAULT_SPECIES_LIST: List[str] = ["American Robin", "Blue Jay", "Northern Cardinal"]
    
    # Storage Volume Paths (Mounted on external SD/SSD)
    STORAGE_BASE_DIR: str = str(BASE_DIR / "data")
    RECORDINGS_DIR: str = str(BASE_DIR / "data" / "recordings")
    SPECTROGRAMS_DIR: str = str(BASE_DIR / "data" / "spectrograms")

    class Config:
        env_prefix = "CHIRPLY_"
        case_sensitive = True

settings = Settings()
