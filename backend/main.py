from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import extract, rag
from config import get_settings

# Get settings
settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for document processing, information extraction, and RAG-based retrieval",
    version="1.0.0"
)

# Configure CORS with specific settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(extract.router, prefix="/api/extract", tags=["extraction"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/hello")
async def read_root():
    return {"message": "Hello from FastAPI!"} 