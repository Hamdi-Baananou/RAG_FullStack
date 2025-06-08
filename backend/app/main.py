from fastapi import FastAPI, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from routers import extract, rag
from typing import List, Optional
from fastapi import File, Depends

app = FastAPI(title="RAG API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(extract.router, prefix="/api/extract", tags=["extract"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])

@app.get("/")
async def root():
    return {"message": "Welcome to the RAG API"}

@app.post("/process", response_model=List[ExtractionResult])
async def process_file(
    file: UploadFile = File(...),
    part_number: Optional[str] = Form(None),
    attributes: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    llm_service: LLMInterface = Depends(get_llm_service),
    pdf_service: PDFProcessor = Depends(get_pdf_service),
    vector_store: VectorStore = Depends(get_vector_store),
    web_scraper: WebScraper = Depends(get_web_scraper)
):
    # Implementation of the endpoint
    pass 