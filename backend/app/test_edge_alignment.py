import os
import sys
import logging
from pathlib import Path

# Add backend to path to allow importing app modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Setup logging to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("chirply.test_alignment")

def test_config():
    logger.info("--- Testing Configuration Path Resolution ---")
    from backend.app.core.config import settings
    logger.info(f"BASE_DIR: {settings.STORAGE_BASE_DIR}")
    logger.info(f"DB_PATH: {settings.DB_PATH}")
    logger.info(f"RECORDINGS_DIR: {settings.RECORDINGS_DIR}")
    logger.info(f"SPECTROGRAMS_DIR: {settings.SPECTROGRAMS_DIR}")
    logger.info(f"MODEL_PATH: {settings.BIRDNET_MODEL_PATH}")
    logger.info(f"LABELS_PATH: {settings.BIRDNET_LABELS_PATH}")
    
    # Assert paths resolve inside the workspace
    assert "data" in settings.STORAGE_BASE_DIR, "Storage dir should point to workspace data folder"
    assert "chirply.db" in settings.DB_PATH, "DB path should point to chirply.db"
    logger.info("Configuration checks passed!")

def test_database_logger():
    logger.info("--- Testing Database Logger (SQLite Local) ---")
    from backend.app.core.config import settings
    from backend.app.services.detection_logger import DetectionLoggerService
    
    # Instantiate logger with configuration path
    db_service = DetectionLoggerService(db_path=settings.DB_PATH)
    logger.info(f"Initializing database at: {db_service.db_path}")
    db_service.initialize_database()
    
    # Log a mock species detection
    logger.info("Logging dummy detection...")
    det_id = db_service.log_detection(
        scientific_name="Turdus migratorius",
        common_name="American Robin",
        confidence=0.92,
        audio_file="rec_mock_test.wav",
        spectrogram_file="spec_mock_test.png"
    )
    logger.info(f"Logged detection success, ID: {det_id}")
    
    # Fetch recent detections and verify
    logger.info("Fetching logged detections...")
    results = db_service.fetch_recent_detections(limit=5)
    logger.info(f"Found {len(results)} detections in local database.")
    for r in results:
        logger.info(f"  [{r['timestamp']}] {r['common_name']} - {r['confidence']:.2%}")
        
    assert len(results) > 0, "Database query returned 0 results after write"
    assert results[0]["id"] == det_id, "Fetched ID does not match logged ID"
    logger.info("Database logging checks passed!")

def test_audio_recorder():
    logger.info("--- Testing Audio Recorder Mock Mode ---")
    from backend.app.core.config import settings
    from backend.app.services.audio_recorder import AudioRecorderService
    
    recorder = AudioRecorderService(output_dir=settings.RECORDINGS_DIR)
    logger.info(f"AudioRecorder mock mode flag: {recorder.mock_mode}")
    
    # Execute a short 1-second mock recording
    logger.info("Starting short 1s recording test...")
    rec_path = recorder.record_audio(duration=1)
    logger.info(f"Recording file generated at: {rec_path}")
    
    assert os.path.exists(rec_path), f"Recording file does not exist: {rec_path}"
    assert os.path.getsize(rec_path) > 0, "Generated WAV file is empty"
    logger.info("Audio recorder checks passed!")

if __name__ == "__main__":
    try:
        test_config()
        test_database_logger()
        test_audio_recorder()
        logger.info("====== ALL STABILIZATION TESTS PASSED SUCCESSFULLY! ======")
    except Exception as e:
        logger.critical(f"STABILIZATION VERIFICATION FAILED: {e}", exc_info=True)
        sys.exit(1)
