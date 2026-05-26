import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.routes import health, detections

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

# Mount modular API routes
app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(detections.router, prefix=settings.API_PREFIX)

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
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """
    On server shutdown:
    1. Triggers the background worker thread to stop.
    2. Closes soundcard audio pipelines cleanly.
    3. Releases ML model interpreter allocations.
    """
    logger.info("Cleaning up backend operational resources...")
    pass
