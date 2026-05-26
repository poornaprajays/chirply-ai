import os
from typing import List
from pydantic_settings import BaseSettings

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
    DB_PATH: str = "/data/detections/chirply.db"
    
    # Audio Ingestion & ReSpeaker Configuration
    AUDIO_SAMPLE_RATE: int = 16000          # 16kHz mono is BirdNET standard
    AUDIO_CHANNELS: int = 1                 # Mono recording
    AUDIO_CHUNK_DURATION_SECONDS: float = 3.0 # BirdNET processes 3-second audio windows
    AUDIO_INPUT_INDEX: int = 1              # Hardware ALSA interface index for ReSpeaker
    
    # Inference Thresholds
    BIRDNET_MODEL_PATH: str = "/app/models/model.tflite"
    MIN_CONFIDENCE_THRESHOLD: float = 0.70  # Default species identification threshold
    DEFAULT_SPECIES_LIST: List[str] = ["American Robin", "Blue Jay", "Northern Cardinal"]
    
    # Storage Volume Paths (Mounted on external SD/SSD)
    STORAGE_BASE_DIR: str = "/data"
    RECORDINGS_DIR: str = "/data/recordings"
    SPECTROGRAMS_DIR: str = "/data/spectrograms"

    class Config:
        env_prefix = "CHIRPLY_"
        case_sensitive = True

settings = Settings()
