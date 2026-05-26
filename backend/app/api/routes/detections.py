from typing import Optional
from fastapi import APIRouter, Query, Path
from backend.app.schemas.detection_schema import DetectionHistorySchema, DetectionResponseSchema

router = APIRouter(prefix="/detections", tags=["Detections & History"])

@router.get("", response_model=DetectionHistorySchema)
async def list_detections(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    species: Optional[str] = Query(None)
):
    """
    Retrieves a paginated list of logged bird acoustic detections,
    supporting filtering by confidence levels and specific species.
    """
    pass

@router.get("/{id}", response_model=DetectionResponseSchema)
async def get_detection_by_id(
    id: str = Path(..., description="Unique detection identifier")
):
    """
    Fetches comprehensive details for a specific bird detection,
    including download links for the WAV clip and PNG spectrogram.
    """
    pass

@router.get("/summary/species")
async def get_species_detected():
    """
    Returns an aggregated list of all bird species detected historically,
    including observation counts.
    """
    pass
