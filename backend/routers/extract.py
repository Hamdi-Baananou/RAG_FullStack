from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, Request
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
import json
import asyncio
from loguru import logger
from datetime import datetime
import os
from pathlib import Path
import time

from services.llm_interface import LLMInterface
from services.pdf_processor import PDFProcessor
from services.vector_store import VectorStore
from services.web_scraper import WebScraper
from config import get_settings

# Import prompts
from prompts.extraction_prompts import get_prompt as get_pdf_prompt
from prompts.extraction_prompts_web import get_prompt as get_web_prompt

router = APIRouter()
settings = get_settings()

# Pydantic models for request/response
class ExtractionRequest(BaseModel):
    part_number: Optional[str] = None
    attributes: Optional[List[str]] = None

    class Config:
        arbitrary_types_allowed = True

class ExtractionResult(BaseModel):
    attribute: str
    value: str
    source: str
    latency: float
    ground_truth: Optional[str] = None
    is_success: bool = False
    is_error: bool = False
    is_not_found: bool = False
    is_rate_limit: bool = False
    exact_match: Optional[bool] = None
    case_insensitive_match: Optional[bool] = None

    class Config:
        arbitrary_types_allowed = True

class MetricsRequest(BaseModel):
    results: List[ExtractionResult]

    class Config:
        arbitrary_types_allowed = True

class MetricsResponse(BaseModel):
    total_fields: int
    success_count: int
    error_count: int
    not_found_count: int
    rate_limit_count: int
    exact_match_count: int
    case_insensitive_match_count: int
    accuracy_denominator: int
    success_rate: float
    error_rate: float
    not_found_rate: float
    rate_limit_rate: float
    exact_match_accuracy: float
    case_insensitive_accuracy: float
    avg_latency: float

    class Config:
        arbitrary_types_allowed = True

# Service dependencies
def get_llm_service():
    return LLMInterface()

def get_pdf_service():
    return PDFProcessor()

def get_vector_store():
    return VectorStore()

def get_web_scraper():
    return WebScraper()

# Define the prompts dictionary using the prompt functions
PROMPTS = {
    # Material Properties
    "Material Filling": {
        "pdf": get_pdf_prompt("material_properties"),
        "web": get_web_prompt("material_properties")
    },
    "Material Name": {
        "pdf": get_pdf_prompt("material_properties", output_format="MATERIAL NAME: [name]"),
        "web": get_web_prompt("material_properties", output_format="MATERIAL NAME: [name]")
    },
    # Physical / Mechanical Attributes
    "Pull-to-Seat": {
        "pdf": get_pdf_prompt("material_properties", output_format="PULL-TO-SEAT: [value]"),
        "web": get_web_prompt("material_properties", output_format="PULL-TO-SEAT: [value]")
    },
    "Gender": {
        "pdf": get_pdf_prompt("material_properties", output_format="GENDER: [value]"),
        "web": get_web_prompt("material_properties", output_format="GENDER: [value]")
    },
    "Height [MM]": {
        "pdf": get_pdf_prompt("material_properties", output_format="HEIGHT: [value] mm"),
        "web": get_web_prompt("material_properties", output_format="HEIGHT: [value] mm")
    },
    "Length [MM]": {
        "pdf": get_pdf_prompt("material_properties", output_format="LENGTH: [value] mm"),
        "web": get_web_prompt("material_properties", output_format="LENGTH: [value] mm")
    },
    "Width [MM]": {
        "pdf": get_pdf_prompt("material_properties", output_format="WIDTH: [value] mm"),
        "web": get_web_prompt("material_properties", output_format="WIDTH: [value] mm")
    },
    "Number of Cavities": {
        "pdf": get_pdf_prompt("material_properties", output_format="NUMBER OF CAVITIES: [value]"),
        "web": get_web_prompt("material_properties", output_format="NUMBER OF CAVITIES: [value]")
    },
    "Number of Rows": {
        "pdf": get_pdf_prompt("material_properties", output_format="NUMBER OF ROWS: [value]"),
        "web": get_web_prompt("material_properties", output_format="NUMBER OF ROWS: [value]")
    },
    "Mechanical Coding": {
        "pdf": get_pdf_prompt("material_properties", output_format="MECHANICAL CODING: [value]"),
        "web": get_web_prompt("material_properties", output_format="MECHANICAL CODING: [value]")
    },
    "Colour": {
        "pdf": get_pdf_prompt("material_properties", output_format="COLOUR: [value]"),
        "web": get_web_prompt("material_properties", output_format="COLOUR: [value]")
    },
    "Colour Coding": {
        "pdf": get_pdf_prompt("material_properties", output_format="COLOUR CODING: [value]"),
        "web": get_web_prompt("material_properties", output_format="COLOUR CODING: [value]")
    },
    # Sealing & Environmental
    "Max. Working Temperature [°C]": {
        "pdf": get_pdf_prompt("material_properties", output_format="MAX WORKING TEMPERATURE: [value] °C"),
        "web": get_web_prompt("material_properties", output_format="MAX WORKING TEMPERATURE: [value] °C")
    },
    "Min. Working Temperature [°C]": {
        "pdf": get_pdf_prompt("material_properties", output_format="MIN WORKING TEMPERATURE: [value] °C"),
        "web": get_web_prompt("material_properties", output_format="MIN WORKING TEMPERATURE: [value] °C")
    },
    "Housing Seal": {
        "pdf": get_pdf_prompt("material_properties", output_format="HOUSING SEAL: [value]"),
        "web": get_web_prompt("material_properties", output_format="HOUSING SEAL: [value]")
    },
    "Wire Seal": {
        "pdf": get_pdf_prompt("material_properties", output_format="WIRE SEAL: [value]"),
        "web": get_web_prompt("material_properties", output_format="WIRE SEAL: [value]")
    },
    "Sealing": {
        "pdf": get_pdf_prompt("material_properties", output_format="SEALING: [value]"),
        "web": get_web_prompt("material_properties", output_format="SEALING: [value]")
    },
    "Sealing Class": {
        "pdf": get_pdf_prompt("material_properties", output_format="SEALING CLASS: [value]"),
        "web": get_web_prompt("material_properties", output_format="SEALING CLASS: [value]")
    },
    # Terminals & Connections
    "Contact Systems": {
        "pdf": get_pdf_prompt("material_properties", output_format="CONTACT SYSTEMS: [value]"),
        "web": get_web_prompt("material_properties", output_format="CONTACT SYSTEMS: [value]")
    },
    "Terminal Position Assurance": {
        "pdf": get_pdf_prompt("material_properties", output_format="TERMINAL POSITION ASSURANCE: [value]"),
        "web": get_web_prompt("material_properties", output_format="TERMINAL POSITION ASSURANCE: [value]")
    },
    "Connector Position Assurance": {
        "pdf": get_pdf_prompt("material_properties", output_format="CONNECTOR POSITION ASSURANCE: [value]"),
        "web": get_web_prompt("material_properties", output_format="CONNECTOR POSITION ASSURANCE: [value]")
    },
    "Closed Cavities": {
        "pdf": get_pdf_prompt("material_properties", output_format="CLOSED CAVITIES: [value]"),
        "web": get_web_prompt("material_properties", output_format="CLOSED CAVITIES: [value]")
    },
    # Assembly & Type
    "Pre-Assembled": {
        "pdf": get_pdf_prompt("material_properties", output_format="PRE-ASSEMBLED: [value]"),
        "web": get_web_prompt("material_properties", output_format="PRE-ASSEMBLED: [value]")
    },
    "Type of Connector": {
        "pdf": get_pdf_prompt("material_properties", output_format="TYPE OF CONNECTOR: [value]"),
        "web": get_web_prompt("material_properties", output_format="TYPE OF CONNECTOR: [value]")
    },
    "Set/Kit": {
        "pdf": get_pdf_prompt("material_properties", output_format="SET/KIT: [value]"),
        "web": get_web_prompt("material_properties", output_format="SET/KIT: [value]")
    },
    # Specialized Attributes
    "HV Qualified": {
        "pdf": get_pdf_prompt("material_properties", output_format="HV QUALIFIED: [value]"),
        "web": get_web_prompt("material_properties", output_format="HV QUALIFIED: [value]")
    }
}

@router.post("/process", response_model=List[ExtractionResult])
async def process_file(
    file: UploadFile = File(...),
    part_number: Optional[str] = Form(None),
    attributes: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    llm_service: LLMInterface = Depends(get_llm_service),
    pdf_service: PDFProcessor = Depends(get_pdf_service),
    vector_store: VectorStore = Depends(get_vector_store),
    web_scraper: WebScraper = Depends(get_web_scraper)
) -> List[ExtractionResult]:
    """
    Process a file and extract attributes using all available services.
    This endpoint handles both PDF files and web URLs.
    """
    try:
        # Parse attributes if provided
        attribute_list = json.loads(attributes) if attributes else None
        
        # Save the uploaded file temporarily
        temp_path = f"temp_{file.filename}"
        try:
            with open(temp_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Process the file
            results = await process_single_file(
                file_path=temp_path,
                part_number=part_number,
                llm_service=llm_service,
                pdf_service=pdf_service,
                vector_store=vector_store,
                web_scraper=web_scraper
            )
            
            # Filter results if specific attributes were requested
            if attribute_list:
                results = [r for r in results if r.attribute in attribute_list]
            
            return results
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_single_file(
    file_path: str,
    part_number: Optional[str],
    llm_service: LLMInterface,
    pdf_service: PDFProcessor,
    vector_store: VectorStore,
    web_scraper: WebScraper
) -> List[ExtractionResult]:
    """
    Process a single file and extract attributes using all available services:
    1. PDFProcessor: Process PDF with Mistral Vision
    2. VectorStore: Store and retrieve PDF chunks
    3. LLMInterface: Handle web scraping and LLM extraction
    """
    results = []
    start_time = time.time()
    
    try:
        # Stage 1: Process PDF using PDFProcessor
        if file_path.endswith('.pdf'):
            # Process PDF using Mistral Vision
            documents = await pdf_service.process_single_pdf(file_path, os.path.basename(file_path))
            if not documents:
                raise ValueError("No text could be extracted from PDF")
            
            # Create vector store with PDF chunks
            retriever = vector_store.create_retriever(documents)
            if not retriever:
                raise ValueError("Failed to create vector store from PDF")
            
            # Stage 2: Extract attributes using LLMInterface's two-stage approach
            for attribute, prompts in PROMPTS.items():
                try:
                    # Use LLMInterface for extraction (it handles web scraping internally)
                    value, source, latency = await llm_service.extract_attribute(
                        attribute_key=attribute,
                        extraction_instructions=prompts['web'],  # Use web prompt as it's more specific
                        part_number=part_number,
                        retriever=retriever
                    )
                    
                    # Create result with proper status flags
                    result = ExtractionResult(
                        attribute=attribute,
                        value=value,
                        source=source,
                        latency=latency,
                        is_success=value != "NOT FOUND",
                        is_error=False,
                        is_not_found=value == "NOT FOUND",
                        is_rate_limit=False
                    )
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error extracting {attribute}: {e}")
                    continue
        else:
            # Handle non-PDF files (e.g., direct web URLs)
            # Use LLMInterface's extract_attribute with no retriever for web-only processing
            for attribute, prompts in PROMPTS.items():
                try:
                    value, source, latency = await llm_service.extract_attribute(
                        attribute_key=attribute,
                        extraction_instructions=prompts['web'],
                        part_number=part_number,
                        retriever=None  # No PDF fallback for web-only processing
                    )
                    
                    result = ExtractionResult(
                        attribute=attribute,
                        value=value,
                        source=source,
                        latency=latency,
                        is_success=value != "NOT FOUND",
                        is_error=False,
                        is_not_found=value == "NOT FOUND",
                        is_rate_limit=False
                    )
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error extracting {attribute}: {e}")
                    continue
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        raise
    
    return results

@router.post("/metrics")
async def calculate_metrics(request: MetricsRequest) -> MetricsResponse:
    """
    Calculate metrics from extraction results.
    """
    try:
        results = request.results
        total_fields = len(results)
        
        # Count different types of results
        success_count = sum(1 for r in results if r.is_success)
        error_count = sum(1 for r in results if r.is_error)
        not_found_count = sum(1 for r in results if r.is_not_found)
        rate_limit_count = sum(1 for r in results if r.is_rate_limit)
        exact_match_count = sum(1 for r in results if r.exact_match)
        case_insensitive_match_count = sum(1 for r in results if r.case_insensitive_match)
        
        # Calculate rates
        success_rate = success_count / total_fields if total_fields > 0 else 0
        error_rate = error_count / total_fields if total_fields > 0 else 0
        not_found_rate = not_found_count / total_fields if total_fields > 0 else 0
        rate_limit_rate = rate_limit_count / total_fields if total_fields > 0 else 0
        
        # Calculate accuracies
        accuracy_denominator = total_fields - not_found_count
        exact_match_accuracy = exact_match_count / accuracy_denominator if accuracy_denominator > 0 else 0
        case_insensitive_accuracy = case_insensitive_match_count / accuracy_denominator if accuracy_denominator > 0 else 0
        
        # Calculate average latency
        avg_latency = sum(r.latency for r in results) / total_fields if total_fields > 0 else 0
        
        return MetricsResponse(
            total_fields=total_fields,
            success_count=success_count,
            error_count=error_count,
            not_found_count=not_found_count,
            rate_limit_count=rate_limit_count,
            exact_match_count=exact_match_count,
            case_insensitive_match_count=case_insensitive_match_count,
            accuracy_denominator=accuracy_denominator,
            success_rate=success_rate,
            error_rate=error_rate,
            not_found_rate=not_found_rate,
            rate_limit_rate=rate_limit_rate,
            exact_match_accuracy=exact_match_accuracy,
            case_insensitive_accuracy=case_insensitive_accuracy,
            avg_latency=avg_latency
        )
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))