"""
PDF ingestion pipeline for processing and indexing PDF documents.
"""
import os
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import PyPDF2
import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract

from ..models.database import db, UploadedFile, IndexingStatus

logger = logging.getLogger(__name__)


class PDFIngestionPipeline:
    """Pipeline for processing PDF files and preparing them for indexing."""
    
    def __init__(self, config, llama_service):
        """Initialize the PDF ingestion pipeline."""
        self.config = config
        self.llama_service = llama_service
        self.books_dir = config.BOOKS_DIR
        self.upload_dir = config.UPLOAD_FOLDER
        
        # Ensure directories exist
        self.books_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def process_uploaded_file(self, file_id: int) -> Dict[str, Any]:
        """Process an uploaded file and move it to the books directory."""
        try:
            # Get file record
            uploaded_file = UploadedFile.query.get(file_id)
            if not uploaded_file:
                return {"status": "error", "message": "File not found"}
            
            if uploaded_file.processed:
                return {"status": "warning", "message": "File already processed"}
            
            # Update status
            uploaded_file.processing_status = "processing"
            db.session.commit()
            
            source_path = Path(uploaded_file.file_path)
            if not source_path.exists():
                uploaded_file.processing_status = "failed"
                uploaded_file.error_message = "Source file not found"
                db.session.commit()
                return {"status": "error", "message": "Source file not found"}
            
            # Extract text to validate PDF
            text_content = self._extract_text_from_pdf(source_path)
            if not text_content or len(text_content.strip()) < 100:
                uploaded_file.processing_status = "failed"
                uploaded_file.error_message = "PDF appears to be empty or unreadable"
                db.session.commit()
                return {"status": "error", "message": "PDF appears to be empty or unreadable"}
            
            # Copy to books directory
            destination_path = self.books_dir / uploaded_file.filename
            shutil.copy2(source_path, destination_path)
            
            # Update file record
            uploaded_file.processed = True
            uploaded_file.processing_status = "completed"
            db.session.commit()
            
            logger.info(f"Successfully processed file: {uploaded_file.filename}")
            return {
                "status": "success",
                "message": f"File processed successfully: {uploaded_file.filename}",
                "text_length": len(text_content)
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_id}: {e}")
            if 'uploaded_file' in locals():
                uploaded_file.processing_status = "failed"
                uploaded_file.error_message = str(e)
                db.session.commit()
            return {"status": "error", "message": str(e)}
    
    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF using multiple methods as fallback."""
        text_content = ""
        
        # Method 1: PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                if text_content.strip():
                    return text_content
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed for {pdf_path}: {e}")
        
        # Method 2: pdfplumber
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                if text_content.strip():
                    return text_content
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed for {pdf_path}: {e}")
        
        # Method 3: pdfminer
        try:
            text_content = pdfminer_extract(str(pdf_path))
            if text_content.strip():
                return text_content
        except Exception as e:
            logger.warning(f"pdfminer extraction failed for {pdf_path}: {e}")
        
        return text_content
    
    def bulk_process_books_directory(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Process all PDF files in the books directory."""
        try:
            # Create indexing status record
            operation_type = "full_rebuild" if force_rebuild else "refresh"
            indexing_status = IndexingStatus(
                operation_type=operation_type,
                status="running"
            )
            db.session.add(indexing_status)
            db.session.commit()
            
            pdf_files = list(self.books_dir.glob("*.pdf"))
            indexing_status.total_files = len(pdf_files)
            db.session.commit()
            
            if not pdf_files:
                indexing_status.status = "completed"
                indexing_status.end_time = datetime.utcnow()
                db.session.commit()
                return {"status": "warning", "message": "No PDF files found in books directory"}
            
            # Validate all PDFs first
            valid_files = []
            for pdf_file in pdf_files:
                text = self._extract_text_from_pdf(pdf_file)
                if text and len(text.strip()) >= 100:
                    valid_files.append(pdf_file)
                    logger.info(f"Validated PDF: {pdf_file.name}")
                else:
                    logger.warning(f"Skipping invalid PDF: {pdf_file.name}")
            
            indexing_status.files_processed = len(valid_files)
            db.session.commit()
            
            if not valid_files:
                indexing_status.status = "failed"
                indexing_status.error_message = "No valid PDF files found"
                indexing_status.end_time = datetime.utcnow()
                db.session.commit()
                return {"status": "error", "message": "No valid PDF files found"}
            
            # Refresh the vector index
            refresh_result = self.llama_service.refresh_index(force_rebuild=force_rebuild)
            
            # Update indexing status
            if refresh_result["status"] == "success":
                indexing_status.status = "completed"
            else:
                indexing_status.status = "failed"
                indexing_status.error_message = refresh_result.get("message", "Unknown error")
            
            indexing_status.end_time = datetime.utcnow()
            db.session.commit()
            
            return {
                "status": refresh_result["status"],
                "message": f"Processed {len(valid_files)} valid PDFs. {refresh_result['message']}",
                "valid_files": len(valid_files),
                "total_files": len(pdf_files),
                "indexing_result": refresh_result
            }
            
        except Exception as e:
            logger.error(f"Error in bulk processing: {e}")
            if 'indexing_status' in locals():
                indexing_status.status = "failed"
                indexing_status.error_message = str(e)
                indexing_status.end_time = datetime.utcnow()
                db.session.commit()
            return {"status": "error", "message": str(e)}
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Get the current processing status."""
        try:
            # Get latest indexing status
            latest_indexing = IndexingStatus.query.order_by(
                IndexingStatus.start_time.desc()
            ).first()
            
            # Get unprocessed files
            unprocessed_files = UploadedFile.query.filter_by(processed=False).all()
            
            # Get books directory stats
            books_count = len(list(self.books_dir.glob("*.pdf")))
            
            return {
                "status": "success",
                "latest_indexing": latest_indexing.to_dict() if latest_indexing else None,
                "unprocessed_uploads": len(unprocessed_files),
                "books_directory_count": books_count,
                "books_directory_path": str(self.books_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting processing status: {e}")
            return {"status": "error", "message": str(e)}
    
    def cleanup_old_uploads(self, days: int = 7) -> Dict[str, Any]:
        """Clean up old uploaded files that have been processed."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            old_files = UploadedFile.query.filter(
                UploadedFile.processed == True,
                UploadedFile.upload_timestamp < cutoff_date
            ).all()
            
            deleted_count = 0
            for file_record in old_files:
                try:
                    file_path = Path(file_record.file_path)
                    if file_path.exists():
                        file_path.unlink()
                    db.session.delete(file_record)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Could not delete file {file_record.filename}: {e}")
            
            db.session.commit()
            
            return {
                "status": "success",
                "message": f"Cleaned up {deleted_count} old uploaded files",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"status": "error", "message": str(e)}
