import os
import time
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.routes import health, detections, stats

# Configure standard Python logging format suitable for systemd monitoring
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("chirply.main")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.APP_NAME else None, # Serve swagger specs locally on edge
)

# Enable CORS for local React app iteration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tighten down during edge production config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular API routers
app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(detections.router, prefix=settings.API_PREFIX)
app.include_router(detections.assets_router, prefix=settings.API_PREFIX)
app.include_router(stats.router, prefix=settings.API_PREFIX)

@app.on_event("startup")
async def startup_event():
    """
    On server startup:
    1. Triggers directory checks using FileUtils to verify /data is ready.
    2. Initializes SQLite tables via DetectionLoggerService.
    3. Pre-loads the BirdNET TF Lite model.
    4. Launches the RealtimeInferencePipeline in a background worker thread.
    """
    logger.info("Initializing chirply-ai backend services...")
    
    # Store startup time for health uptime calculation
    app.state.startup_time = time.time()
    
    # Import service modules inside startup hook to prevent circular dependencies
    from backend.app.utils.file_utils import FileUtils
    from backend.app.services.detection_logger import DetectionLoggerService
    from backend.app.services.birdnet_service import BirdNetService
    from backend.app.services.spectrogram_service import SpectrogramService
    from backend.app.services.audio_recorder import AudioRecorderService
    from backend.app.pipelines.realtime_pipeline import RealtimeInferencePipeline

    # 1. Provision folder writes structure on disk
    FileUtils.ensure_directories_exist([
        settings.STORAGE_BASE_DIR,
        settings.RECORDINGS_DIR,
        settings.SPECTROGRAMS_DIR,
        os.path.dirname(settings.DB_PATH)
    ])
    
    # 2. Instantiate and provision database schemas
    db_logger = DetectionLoggerService(db_path=settings.DB_PATH)
    db_logger.initialize_database()
    
    # 3. Instantiate other background services
    birdnet = BirdNetService()
    spectrogram = SpectrogramService()
    recorder = AudioRecorderService(output_dir=settings.RECORDINGS_DIR)
    
    # 4. Instantiate background pipeline orchestrator
    pipeline = RealtimeInferencePipeline(
        recorder=recorder,
        birdnet=birdnet,
        spectrogram=spectrogram,
        db_logger=db_logger
    )
    
    # 5. Bind elements onto app state to share dependencies across routes
    app.state.db_logger = db_logger
    app.state.birdnet = birdnet
    app.state.spectrogram = spectrogram
    app.state.recorder = recorder
    app.state.pipeline = pipeline
    
    # 6. Spawn background loop thread execution
    pipeline.start()
    logger.info("chirply-ai backend services initialized successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    On server shutdown:
    1. Triggers the background worker thread to stop.
    2. Closes soundcard audio pipelines cleanly.
    3. Releases ML model interpreter allocations.
    """
    logger.info("Cleaning up backend operational resources...")
    pipeline = getattr(app.state, "pipeline", None)
    if pipeline:
        pipeline.stop()
    logger.info("Operational cleanup complete.")
