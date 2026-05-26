from fastapi import APIRouter
from backend.app.schemas.detection_schema import SystemStatusSchema

router = APIRouter(prefix="/health", tags=["System & Health"])

@router.get("", response_model=SystemStatusSchema)
async def check_system_health():
    """
    Diagnostics route for verifying hardware and ingestion health.
    Calculates Raspberry Pi temperature metrics, memory load, and soundcard levels.
    """
    pass
