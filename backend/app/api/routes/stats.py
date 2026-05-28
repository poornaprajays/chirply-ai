import os
import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, Request
from backend.app.schemas.detection_schema import StatsResponseSchema
from backend.app.core.config import settings

logger = logging.getLogger("chirply.api.stats")
router = APIRouter(prefix="/stats", tags=["System Analytics"])

def calculate_storage_utilization() -> dict:
    """
    Computes storage size and file counts for visual/audio directories.
    """
    recordings_dir = Path(settings.RECORDINGS_DIR)
    spectrograms_dir = Path(settings.SPECTROGRAMS_DIR)
    db_path = Path(settings.DB_PATH)
    
    def get_dir_size_and_count(directory: Path):
        size = 0
        count = 0
        if directory.exists():
            for f in directory.iterdir():
                if f.is_file():
                    size += f.stat().st_size
                    count += 1
        return size, count
        
    rec_size, rec_count = get_dir_size_and_count(recordings_dir)
    spec_size, spec_count = get_dir_size_and_count(spectrograms_dir)
    
    db_size = db_path.stat().st_size if db_path.exists() else 0
    
    # Calculate disk usage of settings.STORAGE_BASE_DIR directory
    try:
        total, used, free = shutil.disk_usage(settings.STORAGE_BASE_DIR)
    except FileNotFoundError:
        # Fallback if base directory is missing or not yet provisioned
        total, used, free = 0, 0, 0
        
    return {
        "recordings_count": rec_count,
        "recordings_size_bytes": rec_size,
        "spectrograms_count": spec_count,
        "spectrograms_size_bytes": spec_size,
        "database_size_bytes": db_size,
        "disk_total_bytes": total,
        "disk_used_bytes": used,
        "disk_free_bytes": free,
        "disk_free_percent": (free / total) * 100.0 if total > 0 else 0.0
    }

@router.get("", response_model=StatsResponseSchema)
async def get_system_statistics(request: Request):
    """
    Returns global system analytics and local storage utilization summary.
    """
    db_logger = getattr(request.app.state, "db_logger", None)
    if db_logger is None:
        db_stats = {
            "total_detections": 0,
            "unique_species_count": 0,
            "most_frequent_species": [],
            "average_confidence": 0.0
        }
    else:
        db_stats = db_logger.get_statistics()
        
    storage_stats = calculate_storage_utilization()
    
    return {
        "total_detections": db_stats["total_detections"],
        "unique_species_count": db_stats["unique_species_count"],
        "most_frequent_species": db_stats["most_frequent_species"],
        "average_confidence": db_stats["average_confidence"],
        "storage_utilization": storage_stats
    }
