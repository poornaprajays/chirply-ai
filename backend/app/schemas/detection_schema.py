from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DetectionBaseSchema(BaseModel):
    """
    Common data model attributes for bird acoustic detections.
    """
    species_common: str = Field(..., description="Common name of detected bird species")
    species_scientific: str = Field(..., description="Scientific classification name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Inference certainty score")

class DetectionCreateSchema(DetectionBaseSchema):
    """
    Properties needed to log a new acoustic occurrence in the database.
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    audio_file: str = Field(..., description="Relative path to WAV clip inside storage volume")
    spectrogram_file: str = Field(..., description="Relative path to PNG spectrogram print")

class DetectionResponseSchema(DetectionBaseSchema):
    """
    Response schema returning detection details to frontend.
    """
    id: str = Field(..., description="Unique detection database identifier")
    timestamp: datetime
    audio_url: str = Field(..., description="HTTP REST link to stream target WAV file")
    spectrogram_url: str = Field(..., description="HTTP REST link to load PNG spectrogram")
    
    class Config:
        from_attributes = True

class DetectionHistorySchema(BaseModel):
    """
    Unified pagination wrap for querying log histories.
    """
    total: int = Field(..., description="Total available records matching filters")
    limit: int
    offset: int
    results: List[DetectionResponseSchema]

class HardwareStatusSchema(BaseModel):
    """
    Raspberry Pi metrics status shape.
    """
    cpu_usage_percent: float
    cpu_temperature_celsius: float
    ram_used_mb: int
    ram_total_mb: int
    disk_free_percent: float

class TelemetryStatusSchema(BaseModel):
    """
    Continuous pipeline telemetry logs and storage layout path details.
    """
    uptime_seconds: int
    total_processed_chunks: int
    total_detections: int
    last_run_timestamp: Optional[str] = None
    system_mode: str
    database_path: str
    recordings_dir: str
    spectrograms_dir: str

class SystemStatusSchema(BaseModel):
    """
    Diagnostics response format.
    """
    status: str = Field("healthy", description="Global health label")
    pipeline_active: bool = Field(..., description="Whether recording pipeline is active")
    hardware: HardwareStatusSchema
    microphone_level_db: float = Field(..., description="Live decibel indicator from soundcard")
    telemetry: TelemetryStatusSchema

class SpeciesCountSchema(BaseModel):
    """
    Species observation metrics item.
    """
    common_name: str
    count: int

class StatsResponseSchema(BaseModel):
    """
    Global system analytics summary schema.
    """
    total_detections: int
    unique_species_count: int
    most_frequent_species: List[SpeciesCountSchema]
    average_confidence: float
    storage_utilization: Dict[str, Any]
