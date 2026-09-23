import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import db_manager
from app.routers import cases, evidence, analysis, reports

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("investigation.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI Cyber Investigation Assistant Backend...")
    await db_manager.connect()
    yield
    logger.info("Shutting down backend...")
    await db_manager.close()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Digital Evidence Intelligence & Cyber Investigation API",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(analysis.router)
app.include_router(reports.router)

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "database": "connected (Atlas)" if db_manager.is_live_mongo else "connected (Local Resilient)",
        "groq_configured": bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here"),
        "gemini_configured": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "AI Cyber Investigation Assistant API is operational.",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
