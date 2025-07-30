"""
PDF ingestion pipeline for processing and indexing PDF documents.
Enhanced with citation and page number tracking.
"""
import os
import logging
import shutil
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import PyPDF2
import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract

from ..models.database import db, UploadedFile, IndexingStatus

logger = logging.getLogger(__name__)


class EnhancedDocumentChunk:
    """Enhanced document chunk with citation metadata."""
    
    def __init__(self, content: str, book_name: str, page_number: int, 
                 chunk_index: int, start_char: int = 0, end_char: int = 0):
        self.content = content
        self.book_name = book_name
        self.page_number = page_number
        self.chunk_index = chunk_index
        self.start_char = start_char
        self.end_char = end_char
        self.metadata = self._create_metadata()
    
    def _create_metadata(self) -> Dict[str, Any]:
        """Create metadata dictionary for vector storage."""
        return {
            'book_name': self.book_name,
            'page_number': self.page_number,
            'chunk_index': self.chunk_index,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'source_id': f"{self.book_name}_p{self.page_number}_c{self.chunk_index}",
            'content_preview': self.content[:100] + "..." if len(self.content) > 100 else self.content
        }


class PDFIngestionPipeline:
    """Pipeline for processing PDF files and preparing them for indexing."""
    
    def __init__(self, config, llama_service):
        """Initialize the PDF ingestion pipeline."""
        self.config = config
        self.llama_service = llama_service
        self.books_dir = config.BOOKS_DIR
        self.upload_dir = config.UPLOAD_FOLDER
        
        # Enhanced chunking parameters for better citation accuracy
        self.chunk_size = 800  # Increased for better context
        self.overlap = 100     # Optimized overlap
        
        # Ensure directories exist
        self.books_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_book_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract comprehensive book metadata including title."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata = pdf_reader.metadata or {}
                
                # Try multiple methods to get book title
                book_name = (
                    metadata.get('/Title') or
                    metadata.get('Title') or
                    self._extract_title_from_first_page(pdf_path) or
                    self._get_filename_as_title(pdf_path)
                )
                
                # Clean the book name
                book_name = self._clean_book_name(book_name)
                
                return {
                    'book_name': book_name,
                    'total_pages': len(pdf_reader.pages),
                    'author': metadata.get('/Author') or metadata.get('Author', 'Unknown'),
                    'subject': metadata.get('/Subject') or metadata.get('Subject', ''),
                    'creator': metadata.get('/Creator') or metadata.get('Creator', ''),
                    'file_path': str(pdf_path)
                }
        except Exception as e:
            logger.warning(f"Error extracting metadata from {pdf_path}: {e}")
            return {
                'book_name': self._get_filename_as_title(pdf_path),
                'total_pages': 0,
                'author': 'Unknown',
                'subject': '',
                'creator': '',
                'file_path': str(pdf_path)
            }
    
    def _extract_title_from_first_page(self, pdf_path: Path) -> Optional[str]:
        """Extract title from the first page of PDF."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text()
                    if first_page_text:
                        # Look for title patterns (usually in first few lines and larger font)
                        lines = first_page_text.strip().split('\n')[:5]
                        for line in lines:
                            line = line.strip()
                            if len(line) > 10 and len(line) < 100 and not re.search(r'\d{4}|\bemail\b|@|\.com', line.lower()):
                                return line
        except Exception as e:
            logger.warning(f"Could not extract title from first page: {e}")
        return None
    
    def _get_filename_as_title(self, pdf_path: Path) -> str:
        """Get book title from filename as fallback."""
        filename = pdf_path.stem
        # Clean up filename to make it more readable
        title = re.sub(r'[-_]', ' ', filename)
        title = re.sub(r'\s+', ' ', title)
        return title.title()
    
    def _clean_book_name(self, book_name: str) -> str:
        """Clean and normalize book name."""
        if not book_name:
            return "Unknown Book"
        
        # Remove excessive whitespace and normalize
        book_name = re.sub(r'\s+', ' ', book_name.strip())
        
        # Remove common PDF artifacts
        book_name = re.sub(r'Microsoft Word - |\.pdf$|\.docx?$', '', book_name, flags=re.IGNORECASE)
        
        # Ensure reasonable length
        if len(book_name) > 100:
            book_name = book_name[:97] + "..."
        
        return book_name or "Unknown Book"
    
    def extract_text_with_pages(self, pdf_path: Path) -> List[Tuple[int, str]]:
        """Extract text from PDF maintaining page number information."""
        pages_text = []
        
        try:
            # Use pdfplumber for better page-by-page extraction
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            pages_text.append((page_num, page_text.strip()))
                        else:
                            logger.warning(f"Empty page {page_num} in {pdf_path.name}")
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num} from {pdf_path.name}: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {e}")
            # Fallback to PyPDF2
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        try:
                            page_text = page.extract_text()
                            if page_text and page_text.strip():
                                pages_text.append((page_num, page_text.strip()))
                        except Exception as pe:
                            logger.warning(f"PyPDF2 error on page {page_num}: {pe}")
                            continue
            except Exception as fallback_error:
                logger.error(f"Both pdfplumber and PyPDF2 failed for {pdf_path}: {fallback_error}")
        
        return pages_text
    
    def create_enhanced_chunks(self, pages_text: List[Tuple[int, str]], book_name: str) -> List[EnhancedDocumentChunk]:
        """Create enhanced document chunks with citation metadata."""
        chunks = []
        
        for page_num, page_text in pages_text:
            page_chunks = self._create_page_chunks(page_text, book_name, page_num)
            chunks.extend(page_chunks)
        
        logger.info(f"Created {len(chunks)} enhanced chunks for {book_name}")
        return chunks
    
    def _create_page_chunks(self, page_text: str, book_name: str, page_num: int) -> List[EnhancedDocumentChunk]:
        """Create overlapping chunks for a single page while maintaining context."""
        chunks = []
        text_length = len(page_text)
        
        if text_length <= self.chunk_size:
            # Page fits in one chunk
            chunk = EnhancedDocumentChunk(
                content=page_text,
                book_name=book_name,
                page_number=page_num,
                chunk_index=0,
                start_char=0,
                end_char=text_length
            )
            chunks.append(chunk)
        else:
            # Create overlapping chunks
            chunk_index = 0
            for i in range(0, text_length, self.chunk_size - self.overlap):
                chunk_text = page_text[i:i + self.chunk_size]
                
                # Ensure we don't break words at chunk boundaries
                if i + self.chunk_size < text_length:
                    # Find the last complete sentence or word
                    last_sentence = chunk_text.rfind('.')
                    last_space = chunk_text.rfind(' ')
                    
                    if last_sentence > len(chunk_text) * 0.8:  # If sentence end is near the end
                        chunk_text = chunk_text[:last_sentence + 1]
                    elif last_space > len(chunk_text) * 0.8:  # If space is near the end
                        chunk_text = chunk_text[:last_space]
                
                if chunk_text.strip():  # Only add non-empty chunks
                    chunk = EnhancedDocumentChunk(
                        content=chunk_text.strip(),
                        book_name=book_name,
                        page_number=page_num,
                        chunk_index=chunk_index,
                        start_char=i,
                        end_char=min(i + len(chunk_text), text_length)
                    )
                    chunks.append(chunk)
                    chunk_index += 1
        
        return chunks
    
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
            
            # Enhanced validation with page-by-page extraction
            pages_text = self.extract_text_with_pages(source_path)
            if not pages_text or len(pages_text) == 0:
                uploaded_file.processing_status = "failed"
                uploaded_file.error_message = "PDF appears to be empty or unreadable"
                db.session.commit()
                return {"status": "error", "message": "PDF appears to be empty or unreadable"}
            
            # Validate content quality
            total_text_length = sum(len(page_text) for _, page_text in pages_text)
            if total_text_length < 100:
                uploaded_file.processing_status = "failed"
                uploaded_file.error_message = "PDF content too short or corrupted"
                db.session.commit()
                return {"status": "error", "message": "PDF content too short or corrupted"}
            
            # Copy to books directory
            destination_path = self.books_dir / uploaded_file.filename
            shutil.copy2(source_path, destination_path)
            
            # Update file record
            uploaded_file.processed = True
            uploaded_file.processing_status = "completed"
            db.session.commit()
            
            logger.info(f"Successfully processed file: {uploaded_file.filename} ({len(pages_text)} pages)")
            return {
                "status": "success",
                "message": f"File processed successfully: {uploaded_file.filename}",
                "text_length": total_text_length,
                "page_count": len(pages_text)
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
        """Process all PDF files in the books directory with enhanced citation extraction."""
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
            
            # Enhanced validation and processing with citation extraction
            valid_files = []
            enhanced_chunks_data = []
            
            for pdf_file in pdf_files:
                try:
                    # Extract metadata first
                    book_metadata = self.extract_book_metadata(pdf_file)
                    
                    # Extract text with page information
                    pages_text = self.extract_text_with_pages(pdf_file)
                    
                    if pages_text and len(pages_text) > 0:
                        total_text = sum(len(page_text) for _, page_text in pages_text)
                        if total_text >= 100:  # Minimum text threshold
                            # Create enhanced chunks with citation metadata
                            enhanced_chunks = self.create_enhanced_chunks(pages_text, book_metadata['book_name'])
                            
                            valid_files.append(pdf_file)
                            enhanced_chunks_data.append({
                                'file_path': str(pdf_file),
                                'metadata': book_metadata,
                                'chunks': enhanced_chunks
                            })
                            
                            logger.info(f"Processed {pdf_file.name}: {len(enhanced_chunks)} chunks from {len(pages_text)} pages")
                        else:
                            logger.warning(f"Skipping {pdf_file.name}: insufficient content")
                    else:
                        logger.warning(f"Skipping {pdf_file.name}: no readable text found")
                        
                except Exception as e:
                    logger.error(f"Error processing {pdf_file.name}: {e}")
                    continue
            
            indexing_status.files_processed = len(valid_files)
            db.session.commit()
            
            if not valid_files:
                indexing_status.status = "failed"
                indexing_status.error_message = "No valid PDF files found"
                indexing_status.end_time = datetime.utcnow()
                db.session.commit()
                return {"status": "error", "message": "No valid PDF files found"}
            
            # Pass enhanced chunks data to llama service for indexing
            refresh_result = self.llama_service.refresh_index_with_citations(
                enhanced_chunks_data, 
                force_rebuild=force_rebuild
            )
            
            # Update indexing status
            if refresh_result["status"] == "success":
                indexing_status.status = "completed"
            else:
                indexing_status.status = "failed"
                indexing_status.error_message = refresh_result.get("message", "Unknown error")
            
            indexing_status.end_time = datetime.utcnow()
            db.session.commit()
            
            total_chunks = sum(len(data['chunks']) for data in enhanced_chunks_data)
            
            return {
                "status": refresh_result["status"],
                "message": f"Processed {len(valid_files)} PDFs with {total_chunks} chunks. {refresh_result['message']}",
                "valid_files": len(valid_files),
                "total_files": len(pdf_files),
                "total_chunks": total_chunks,
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
