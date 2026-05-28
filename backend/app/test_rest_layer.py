import os
import sys
import time
import tempfile
import logging
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend to path to allow importing app modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("chirply.test_rest")

def test_rest_endpoints():
    logger.info("=== Starting REST API Layer Verification ===")
    from backend.app.main import app
    from backend.app.core.config import settings
    from backend.app.services.detection_logger import DetectionLoggerService
    from backend.app.services.audio_recorder import AudioRecorderService
    from backend.app.pipelines.realtime_pipeline import RealtimeInferencePipeline
    
    # 1. Create a clean temporary DB path for the test run
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(temp_db_fd)
    
    db_logger = DetectionLoggerService(db_path=temp_db_path)
    db_logger.initialize_database()
    
    # Log a dummy species to query
    det_id = db_logger.log_detection(
        scientific_name="Cyanocitta cristata",
        common_name="Blue Jay",
        confidence=0.88,
        audio_file="rec_test_jay.wav",
        spectrogram_file="spec_test_jay.png"
    )
    
    # 2. Setup mock pipeline
    class MockPipeline:
        pipeline_active = True
        total_processed = 12
        total_detections = 1
        last_run_timestamp = "2026-05-28T22:00:00Z"
        def start(self): pass
        def stop(self): pass
        
    class MockRecorder:
        mock_mode = True
        
    pipeline = MockPipeline()
    recorder = MockRecorder()
    
    # 3. Mount dependencies on app.state (simulate startup_event bindings)
    app.state.db_logger = db_logger
    app.state.pipeline = pipeline
    app.state.recorder = recorder
    app.state.startup_time = time.time() - 3600  # 1 hour uptime
    
    # 4. Instantiate FastAPI TestClient
    client = TestClient(app)
    
    # 5. Verify GET /api/v1/health
    logger.info("Testing GET /api/v1/health...")
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200, f"Health endpoint failed: {resp.text}"
    health_data = resp.json()
    assert health_data["status"] == "healthy"
    assert health_data["pipeline_active"] is True
    assert health_data["telemetry"]["system_mode"] == "mock"
    assert health_data["telemetry"]["total_processed_chunks"] == 12
    assert health_data["telemetry"]["total_detections"] == 1
    logger.info("Health API check passed successfully.")
    
    # 6. Verify GET /api/v1/detections
    logger.info("Testing GET /api/v1/detections...")
    resp = client.get("/api/v1/detections")
    assert resp.status_code == 200, f"Detections list endpoint failed: {resp.text}"
    history_data = resp.json()
    assert history_data["total"] == 1
    assert len(history_data["results"]) == 1
    assert history_data["results"][0]["species_common"] == "Blue Jay"
    assert "rec_test_jay.wav" in history_data["results"][0]["audio_url"]
    logger.info("Detections List check passed successfully.")
    
    # 7. Verify GET /api/v1/detections/{id}
    logger.info(f"Testing GET /api/v1/detections/{det_id}...")
    resp = client.get(f"/api/v1/detections/{det_id}")
    assert resp.status_code == 200, f"Detection detail failed: {resp.text}"
    item = resp.json()
    assert item["species_common"] == "Blue Jay"
    assert item["species_scientific"] == "Cyanocitta cristata"
    
    # Test 404 for missing ID
    resp = client.get("/api/v1/detections/det_missing123")
    assert resp.status_code == 404
    logger.info("Detection Detail API check passed successfully.")
    
    # 8. Verify GET /api/v1/detections/summary/species
    logger.info("Testing GET /api/v1/detections/summary/species...")
    resp = client.get("/api/v1/detections/summary/species")
    assert resp.status_code == 200
    species_list = resp.json()
    assert len(species_list) == 1
    assert species_list[0]["species_common"] == "Blue Jay"
    assert species_list[0]["count"] == 1
    logger.info("Species Summary API check passed successfully.")
    
    # 9. Verify GET /api/v1/stats
    logger.info("Testing GET /api/v1/stats...")
    resp = client.get("/api/v1/stats")
    assert resp.status_code == 200
    stats_data = resp.json()
    assert stats_data["total_detections"] == 1
    assert stats_data["unique_species_count"] == 1
    assert len(stats_data["most_frequent_species"]) == 1
    assert stats_data["most_frequent_species"][0]["common_name"] == "Blue Jay"
    assert "storage_utilization" in stats_data
    logger.info("System Statistics API check passed successfully.")
    
    # 10. Verify Safe Media Asset Serving
    logger.info("Testing secure assets routing (invalid filename patterns)...")
    # Invalid extension
    resp = client.get("/api/v1/recordings/test_file.txt")
    assert resp.status_code == 400, f"Expected 400 Bad Request: {resp.status_code}"
    
    # Traversal attack escaping router
    resp = client.get("/api/v1/recordings/../../etc/passwd")
    assert resp.status_code in [400, 403, 404]
    
    # Traversal with valid extension escaping router
    resp = client.get("/api/v1/recordings/../../test.wav")
    assert resp.status_code in [400, 403, 404], f"Expected blocked access: {resp.status_code}"
    logger.info("Secure asset access validation checks passed successfully.")
    
    # 11. Cleanup temporary DB file
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
            if os.path.exists(temp_db_path + "-wal"):
                os.remove(temp_db_path + "-wal")
            if os.path.exists(temp_db_path + "-shm"):
                os.remove(temp_db_path + "-shm")
        except OSError:
            pass
            
    logger.info("====== ALL REST LAYER TESTS PASSED SUCCESSFULLY! ======")

if __name__ == "__main__":
    try:
        test_rest_endpoints()
    except Exception as e:
        logger.critical(f"REST LAYER VERIFICATION FAILED: {e}", exc_info=True)
        sys.exit(1)
