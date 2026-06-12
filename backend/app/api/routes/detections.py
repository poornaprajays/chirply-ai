import os
import re
import logging
from typing import Optional, List
from fastapi import APIRouter, Query, Path, Request, HTTPException
from fastapi.responses import FileResponse
from backend.app.schemas.detection_schema import DetectionHistorySchema, DetectionResponseSchema
from backend.app.core.config import settings

logger = logging.getLogger("chirply.api.detections")

# Modular routes for detections history queries
router = APIRouter(prefix="/detections", tags=["Detections & History"])

# Modular routes for visual/audio file serving with path security
assets_router = APIRouter(tags=["Media Assets"])

@router.get("", response_model=DetectionHistorySchema)
async def list_detections(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    species: Optional[str] = Query(None)
):
    """
    Retrieves a paginated list of logged bird acoustic detections,
    supporting filtering by confidence levels and specific species name searches.
    """
    db_logger = getattr(request.app.state, "db_logger", None)
    if db_logger is None:
        return {
            "total": 0,
            "limit": limit,
            "offset": offset,
            "results": []
        }
        
    # Query matching records
    db_rows = db_logger.fetch_detections(
        limit=limit,
        offset=offset,
        min_confidence=min_confidence,
        species=species
    )
    
    # Query matching counts for metadata
    total_count = db_logger.count_detections(
        min_confidence=min_confidence,
        species=species
    )
    
    # Map raw rows to Pydantic Response schemas
    results = []
    for row in db_rows:
        results.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "species_common": row["common_name"],
            "species_scientific": row["scientific_name"],
            "confidence": row["confidence"],
            "audio_url": f"{settings.API_PREFIX}/recordings/{row['audio_file']}" if row['audio_file'] else "",
            "spectrogram_url": f"{settings.API_PREFIX}/spectrograms/{row['spectrogram_file']}" if row['spectrogram_file'] else ""
        })
        
    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "results": results
    }

@router.get("/summary/species")
async def get_species_detected(request: Request):
    """
    Returns an aggregated list of all bird species detected historically,
    including observation counts.
    """
    db_logger = getattr(request.app.state, "db_logger", None)
    if db_logger is None:
        return []
        
    return db_logger.fetch_species_counts()

@router.get("/{id}", response_model=DetectionResponseSchema)
async def get_detection_by_id(
    request: Request,
    id: str = Path(..., description="Unique detection identifier")
):
    """
    Fetches comprehensive details for a specific bird detection,
    including download links for the WAV clip and PNG spectrogram.
    """
    db_logger = getattr(request.app.state, "db_logger", None)
    if db_logger is None:
        raise HTTPException(status_code=404, detail="Database service not available.")
        
    row = db_logger.fetch_detection_by_id(id)
    if not row:
        logger.warning(f"Query for non-existent detection ID: {id}")
        raise HTTPException(status_code=404, detail="Detection not found.")
        
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "species_common": row["common_name"],
        "species_scientific": row["scientific_name"],
        "confidence": row["confidence"],
        "audio_url": f"{settings.API_PREFIX}/recordings/{row['audio_file']}" if row['audio_file'] else "",
        "spectrogram_url": f"{settings.API_PREFIX}/spectrograms/{row['spectrogram_file']}" if row['spectrogram_file'] else ""
    }


@assets_router.get("/recordings/{filename}")
async def get_recording_file(filename: str):
    """
    Exposes audio recordings WAV files securely with safe path validation.
    """
    # 1. Enforce strict filename formatting to block malicious string uploads
    if not re.match(r"^[a-zA-Z0-9_\-]+\.wav$", filename):
        logger.warning(f"Malicious or invalid recording filename request: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename format.")
        
    # 2. Resolve absolute filesystem location
    file_path = os.path.abspath(os.path.join(settings.RECORDINGS_DIR, filename))
    
    # 3. Secure Path Traversal Auditing
    recordings_dir_abs = os.path.abspath(settings.RECORDINGS_DIR)
    if not file_path.startswith(recordings_dir_abs):
        logger.warning(f"Path traversal exploit blocked on recording: {filename}")
        raise HTTPException(status_code=403, detail="Access denied.")
        
    # 4. Verify existence
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Recording file not found.")
        
    return FileResponse(file_path, media_type="audio/wav")


@assets_router.get("/spectrograms/{filename}")
async def get_spectrogram_file(filename: str):
    """
    Exposes visual spectrogram PNG images securely with safe path validation.
    """
    # 1. Enforce strict filename formatting to block malicious string uploads
    if not re.match(r"^[a-zA-Z0-9_\-]+\.png$", filename):
        logger.warning(f"Malicious or invalid spectrogram filename request: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename format.")
        
    # 2. Resolve absolute filesystem location
    file_path = os.path.abspath(os.path.join(settings.SPECTROGRAMS_DIR, filename))
    
    # 3. Secure Path Traversal Auditing
    spectrograms_dir_abs = os.path.abspath(settings.SPECTROGRAMS_DIR)
    if not file_path.startswith(spectrograms_dir_abs):
        logger.warning(f"Path traversal exploit blocked on spectrogram: {filename}")
        raise HTTPException(status_code=403, detail="Access denied.")
        
    # 4. Verify existence
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Spectrogram file not found.")
        
    return FileResponse(file_path, media_type="image/png")
