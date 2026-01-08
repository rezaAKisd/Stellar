"""FastAPI application entry point"""
import sys
from pathlib import Path

# Add backend directory to Python path for imports
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from api.dependencies import get_state_db, get_file_storage, get_video_composer
from app.infrastructure.task_runner import TaskRunner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Instagram Highlight Downloader API with Clean Architecture",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup() -> None:
    db = get_state_db()
    db.init_schema()  # Initialize base schema
    db.init_schema_v2()  # Run v2 migration
    db.mark_orphaned_tasks_failed()

    # Start background task runner with concurrent workers
    max_workers = getattr(settings, 'TASK_WORKERS', 3)  # Default 3 concurrent tasks
    runner = TaskRunner(db, get_file_storage(), get_video_composer(), max_workers=max_workers)
    runner.start()
    app.state.task_runner = runner
    logger.info(f"Task runner started with {max_workers} concurrent workers")

    # Start cleanup job for 30-day retention policy
    from app.infrastructure.cleanup_job import CleanupJob
    cleanup = CleanupJob(db, settings.DATA_DIR, interval_hours=24)
    cleanup.start()
    app.state.cleanup_job = cleanup
    logger.info("Cleanup job started for 30-day retention policy")


@app.on_event("shutdown")
async def shutdown() -> None:
    # Stop task runner
    runner = getattr(app.state, "task_runner", None)
    if runner is not None:
        await runner.stop()

    # Stop cleanup job
    cleanup = getattr(app.state, "cleanup_job", None)
    if cleanup is not None:
        await cleanup.stop()


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"}
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Stellar Instagram Downloader API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Register routers
from api.routes import auth, highlights, users, files, destinations

app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["auth"])
app.include_router(highlights.router, prefix=f"{settings.API_PREFIX}/highlights", tags=["highlights"])
app.include_router(users.router, prefix=f"{settings.API_PREFIX}/users", tags=["users"])
app.include_router(files.router, prefix=f"{settings.API_PREFIX}/files", tags=["files"])
app.include_router(destinations.router, prefix=f"{settings.API_PREFIX}/destinations", tags=["destinations"])


# WebSocket endpoint for progress updates
from api.websockets import progress

app.include_router(progress.router)


# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

# Note: Static file serving has been replaced with authenticated file routes in Phase 2
# See backend/api/routes/files.py for secure file downloads


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app" if settings.RELOAD else app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level="info",
    )
