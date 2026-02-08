"""FastAPI application"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import router
from db.database import init_db
from config import settings

# Настройка логирования
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    logger.info("Starting Eco Monitor Backend")
    await init_db()
    yield
    logger.info("Shutting down Eco Monitor Backend")


app = FastAPI(
    title="Eco Monitor API",
    description="Мультиагентная система экологического мониторинга",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "eco-monitor"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Eco Monitor API",
        "version": "1.0.0",
        "docs": "/docs"
    }
