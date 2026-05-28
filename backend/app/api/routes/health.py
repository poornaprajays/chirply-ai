import os
import time
import shutil
import logging
from fastapi import APIRouter, Request
from backend.app.schemas.detection_schema import SystemStatusSchema
from backend.app.core.config import settings

logger = logging.getLogger("chirply.api.health")
router = APIRouter(prefix="/health", tags=["System & Health"])

@router.get("", response_model=SystemStatusSchema)
async def check_system_health(request: Request):
    """
    Diagnostics route for verifying hardware and ingestion health.
    Calculates Raspberry Pi temperature metrics, memory load, and soundcard levels.
    """
    app = request.app
    pipeline = getattr(app.state, "pipeline", None)
    recorder = getattr(app.state, "recorder", None)
    
    # Calculate uptime
    uptime_seconds = int(time.time() - getattr(app.state, "startup_time", time.time()))
    
    # Extract pipeline telemetry state
    pipeline_active = getattr(pipeline, "pipeline_active", False) if pipeline else False
    total_processed = getattr(pipeline, "total_processed", 0) if pipeline else 0
    total_detections = getattr(pipeline, "total_detections", 0) if pipeline else 0
    last_run = getattr(pipeline, "last_run_timestamp", None) if pipeline else None
    
    # Retrieve mock/live system status
    is_mock = getattr(recorder, "mock_mode", True) if recorder else True
    mode_str = "mock" if is_mock else "live"
    
    # Hardware stats: CPU and Memory
    cpu_usage = 0.0
    ram_used_mb = 0
    ram_total_mb = 2048
    
    try:
        import psutil
        cpu_usage = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        ram_used_mb = int(ram.used / (1024 * 1024))
        ram_total_mb = int(ram.total / (1024 * 1024))
    except ImportError:
        pass
        
    # Disk Usage
    try:
        total, used, free = shutil.disk_usage(settings.STORAGE_BASE_DIR)
        disk_free_percent = (free / total) * 100.0 if total > 0 else 0.0
    except FileNotFoundError:
        disk_free_percent = 0.0

    # CPU Temperature (Raspberry Pi OS)
    cpu_temp = 0.0
    if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                cpu_temp = float(f.read().strip()) / 1000.0
        except (ValueError, OSError):
            pass
            
    return {
        "status": "healthy" if pipeline_active else "degraded",
        "pipeline_active": pipeline_active,
        "hardware": {
            "cpu_usage_percent": cpu_usage,
            "cpu_temperature_celsius": cpu_temp,
            "ram_used_mb": ram_used_mb,
            "ram_total_mb": ram_total_mb,
            "disk_free_percent": disk_free_percent
        },
        "microphone_level_db": 0.0,  # Live level reading is out of scope for health REST API
        "telemetry": {
            "uptime_seconds": uptime_seconds,
            "total_processed_chunks": total_processed,
            "total_detections": total_detections,
            "last_run_timestamp": last_run,
            "system_mode": mode_str,
            "database_path": settings.DB_PATH,
            "recordings_dir": settings.RECORDINGS_DIR,
            "spectrograms_dir": settings.SPECTROGRAMS_DIR
        }
    }
