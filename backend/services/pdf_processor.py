import os
import re
import base64
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, BinaryIO, Optional, Dict, Any, Tuple
from fastapi import UploadFile
from loguru import logger
from PIL import Image
import fitz  # PyMuPDF
from mistralai import Mistral
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config import get_settings

class PDFProcessor:
    """Service for processing PDF documents using Mistral Vision for text extraction."""
    
    def __init__(self):
        """Initialize the PDF processor with configuration."""
        self.settings = get_settings()
        self.temp_dir = "temp_pdf"
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.CHUNK_SIZE,
            chunk_overlap=self.settings.CHUNK_OVERLAP,
            length_function=len,
            is_separator_regex=False
        )
        self.client = self._initialize_mistral_client()
        
        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)

    def _initialize_mistral_client(self) -> Mistral:
        """Initialize the Mistral client with API key."""
        try:
            client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
            logger.info(f"Initialized Mistral Vision client with model: {self.settings.VISION_MODEL_NAME}")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Mistral client: {e}")
            raise ConnectionError(f"Could not initialize Mistral client: {e}")

    @staticmethod
    def encode_pil_image(pil_image: Image.Image, format: str = "PNG") -> Tuple[str, str]:
        """
        Encode PIL Image to Base64 string.
        
        Args:
            pil_image: PIL Image object to encode
            format: Output format (PNG or JPEG)
            
        Returns:
            Tuple of (base64 string, format)
        """
        buffered = io.BytesIO()
        
        # Ensure image is in RGB mode
        if pil_image.mode == 'RGBA':
            pil_image = pil_image.convert('RGB')
        elif pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        save_format = format.upper()
        if save_format not in ["PNG", "JPEG"]:
            logger.warning(f"Unsupported format '{format}', defaulting to PNG.")
            save_format = "PNG"

        pil_image.save(buffered, format=save_format)
        img_byte = buffered.getvalue()
        return base64.b64encode(img_byte).decode('utf-8'), save_format.lower()

    async def process_pdf(self, file_path: str) -> List[Document]:
        """
        Process a PDF file and return its documents.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of Document objects containing extracted text
        """
        file_basename = os.path.basename(file_path)
        return await self.process_single_pdf(file_path, file_basename)

    async def process_single_pdf(self, file_path: str, file_basename: str) -> List[Document]:
        """
        Process a single PDF file and return its documents.
        
        Args:
            file_path: Path to the PDF file
            file_basename: Base name of the file
            
        Returns:
            List of Document objects containing extracted text
        """
        all_docs = []
        total_pages_processed = 0
        pdf_document = None
        
        try:
            logger.info(f"Processing PDF: {file_basename}")
            pdf_document = fitz.open(file_path)
            total_pages = len(pdf_document)
            logger.info(f"Successfully opened PDF with {total_pages} pages")
            
            markdown_prompt = """
You are an expert document analysis assistant. Extract ALL text content from the image and format it as clean, well-structured GitHub Flavored Markdown.

Follow these formatting instructions:
1. Use appropriate Markdown heading levels based on visual hierarchy
2. Format tables using GitHub Flavored Markdown table syntax
3. Format key-value pairs using bold for keys: `**Key:** Value`
4. Represent checkboxes as `[x]` or `[ ]`
5. Preserve bulleted/numbered lists using standard Markdown syntax
6. Maintain paragraph structure and line breaks
7. Extract text labels from diagrams/images
8. Ensure all visible text is captured accurately

Output only the generated Markdown content.
"""
            
            for page_num in range(total_pages):
                logger.info(f"\n{'='*50}")
                logger.info(f"Processing page {page_num + 1}/{total_pages} of {file_basename}")
                logger.info(f"{'='*50}\n")
                
                try:
                    page = pdf_document[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    base64_image, image_format = self.encode_pil_image(img)
                    
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": markdown_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": f"data:image/{image_format};base64,{base64_image}"
                                }
                            ]
                        }
                    ]
                    
                    logger.info("Sending page to Mistral Vision API...")
                    chat_response = self.client.chat.complete(
                        model=self.settings.VISION_MODEL_NAME,
                        messages=messages
                    )
                    
                    page_content = chat_response.choices[0].message.content
                    
                    if page_content:
                        logger.info("\nExtracted Content:")
                        logger.info("-" * 40)
                        logger.info(page_content)
                        logger.info("-" * 40)
                        
                        chunks = self.text_splitter.split_text(page_content)
                        logger.info(f"\nSplit content into {len(chunks)} chunks")
                        
                        for j, chunk in enumerate(chunks):
                            chunk_doc = Document(
                                page_content=chunk,
                                metadata={
                                    'source': file_basename,
                                    'page': page_num + 1,
                                    'chunk': j + 1,
                                    'total_chunks': len(chunks)
                                }
                            )
                            all_docs.append(chunk_doc)
                        
                        logger.success(f"Successfully processed page {page_num + 1} from {file_basename}")
                        total_pages_processed += 1
                    else:
                        logger.warning(f"No content extracted from page {page_num + 1} of {file_basename}")
                        
                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1} with Mistral Vision: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing {file_basename}: {e}", exc_info=True)
        finally:
            if pdf_document is not None:
                try:
                    pdf_document.close()
                    logger.debug(f"Closed PDF document: {file_basename}")
                except Exception as e:
                    logger.warning(f"Error closing PDF document {file_basename}: {e}")
        
        if not all_docs:
            logger.error(f"No text could be extracted from {file_basename}")
        else:
            logger.info(f"\nProcessing Summary for {file_basename}:")
            logger.info(f"Total pages processed: {total_pages_processed}")
            logger.info(f"Total chunks created: {len(all_docs)}")
        
        return all_docs

    async def process_uploaded_pdfs(self, uploaded_files: List[BinaryIO]) -> List[Document]:
        """
        Process multiple uploaded PDFs in parallel.
        
        Args:
            uploaded_files: List of uploaded PDF files
            
        Returns:
            List of Document objects containing extracted text from all PDFs
        """
        all_docs = []
        saved_file_paths = []
        
        try:
            # Save all files first
            for uploaded_file in uploaded_files:
                file_basename = uploaded_file.name
                file_path = os.path.join(self.temp_dir, file_basename)
                saved_file_paths.append(file_path)
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
            
            # Process PDFs in parallel
            with ThreadPoolExecutor(max_workers=min(len(saved_file_paths), 4)) as executor:
                loop = asyncio.get_event_loop()
                tasks = []
                for file_path in saved_file_paths:
                    file_basename = os.path.basename(file_path)
                    task = loop.run_in_executor(
                        executor,
                        lambda p, b: asyncio.run(self.process_single_pdf(p, b)),
                        file_path,
                        file_basename
                    )
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                for docs in results:
                    if docs:
                        all_docs.extend(docs)
                
        finally:
            # Clean up temporary files
            for path in saved_file_paths:
                try:
                    os.remove(path)
                    logger.debug(f"Removed temporary file: {path}")
                except OSError as e:
                    logger.warning(f"Could not remove temporary file {path}: {e}")
        
        if not all_docs:
            logger.error("No text could be extracted from any provided PDF files.")
        else:
            logger.info("\nFinal Processing Summary:")
            logger.info(f"Total documents processed: {len(saved_file_paths)}")
            logger.info(f"Total chunks created: {len(all_docs)}")
        
        return all_docs

    async def validate_file(self, file: UploadFile) -> bool:
        """
        Validate if the uploaded file is a valid PDF.
        
        Args:
            file: Uploaded file to validate
            
        Returns:
            True if file is valid, False otherwise
        """
        if not file.filename:
            return False
            
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.pdf']:
            return False
            
        try:
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            return content.startswith(b'%PDF-')
        except Exception as e:
            logger.error(f"Error validating file {file.filename}: {e}")
            return False

    async def extract_text(self, file: UploadFile) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            file: Uploaded PDF file
            
        Returns:
            Extracted text as string
        """
        try:
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Save to temporary file
            temp_path = os.path.join(self.temp_dir, file.filename)
            with open(temp_path, "wb") as f:
                f.write(content)
            
            # Process PDF
            docs = await self.process_pdf(temp_path)
            
            # Clean up
            try:
                os.remove(temp_path)
            except OSError as e:
                logger.warning(f"Could not remove temporary file {temp_path}: {e}")
            
            # Combine all text
            return "\n\n".join(doc.page_content for doc in docs)
            
        except Exception as e:
            logger.error(f"Error extracting text from {file.filename}: {e}")
            return ""

    async def extract_metadata(self, file: UploadFile) -> Dict[str, Any]:
        """
        Extract metadata from a PDF file.
        
        Args:
            file: Uploaded PDF file
            
        Returns:
            Dictionary containing metadata
        """
        try:
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Save to temporary file
            temp_path = os.path.join(self.temp_dir, file.filename)
            with open(temp_path, "wb") as f:
                f.write(content)
            
            # Extract metadata
            pdf_document = fitz.open(temp_path)
            metadata = pdf_document.metadata
            
            # Clean up
            pdf_document.close()
            try:
                os.remove(temp_path)
            except OSError as e:
                logger.warning(f"Could not remove temporary file {temp_path}: {e}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file.filename}: {e}")
            return {}

    async def process_pdfs_in_background(self, uploaded_files: List[BinaryIO]) -> asyncio.Task:
        """
        Start PDF processing in the background.
        
        Args:
            uploaded_files: List of uploaded PDF files
            
        Returns:
            asyncio.Task that can be awaited for results
        """
        return asyncio.create_task(self.process_uploaded_pdfs(uploaded_files)) 