from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import tempfile
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import chromadb
from chromadb.config import Settings
from config import get_settings

router = APIRouter(
    prefix="/rag",
    tags=["rag"],
    responses={404: {"description": "Not found"}},
)

# Get settings
settings = get_settings()

# Initialize ChromaDB
chroma_client = chromadb.Client(Settings(
    persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
    anonymized_telemetry=False
))

# Create or get collection
collection = chroma_client.get_or_create_collection(
    name=settings.COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)

class Query(BaseModel):
    text: str
    n_results: Optional[int] = settings.RETRIEVER_K

class DocumentResponse(BaseModel):
    text: str
    metadata: dict

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE/1024/1024}MB")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        # Load and process PDF
        loader = PyPDFLoader(temp_file_path)
        pages = loader.load()
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )
        chunks = text_splitter.split_documents(pages)
        
        # Add documents to ChromaDB
        for i, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk.page_content],
                metadatas=[{
                    "source": file.filename,
                    "page": chunk.metadata.get("page", 0),
                    "chunk": i
                }],
                ids=[f"{file.filename}_{i}"]
            )
        
        return {"message": f"Successfully processed {len(chunks)} chunks from {file.filename}"}
    
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

@router.post("/query", response_model=List[DocumentResponse])
async def query_documents(query: Query):
    results = collection.query(
        query_texts=[query.text],
        n_results=query.n_results
    )
    
    return [
        DocumentResponse(
            text=doc,
            metadata=meta
        )
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ] 