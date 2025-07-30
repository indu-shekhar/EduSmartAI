"""
Enhanced PDF Processor with multiple extraction methods and quality assessment.
Designed to fix text extraction issues causing poor LlamaIndex responses.
"""

import logging
import re
import fitz  # PyMuPDF
import pdfplumber
import PyPDF2
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class TextQualityMetrics:
    """Metrics for assessing text extraction quality."""
    unicode_artifacts: int = 0
    garbled_chars: int = 0
    readable_words: int = 0
    total_chars: int = 0
    valid_sentences: int = 0
    quality_score: float = 0.0

@dataclass
class ExtractionResult:
    """Result from a PDF text extraction method."""
    text: str
    page_number: int
    method: str
    quality_metrics: TextQualityMetrics
    success: bool = True
    error: Optional[str] = None

class EnhancedPDFProcessor:
    """Enhanced PDF processor with multiple extraction methods and quality assessment."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Unicode artifacts and garbled character patterns
        self.unicode_artifacts_pattern = re.compile(r'[\uf000-\uf8ff]|[\ue000-\uf8ff]')
        self.garbled_patterns = [
            re.compile(r'[^\w\s\.\,\!\?\:\;\-\(\)\[\]\{\}\"\'\/\\]'),
            re.compile(r'[A-Z]{5,}'),  # Too many consecutive capitals
            re.compile(r'\s{3,}'),     # Excessive whitespace
        ]
        
        # Quality thresholds
        self.min_quality_score = 0.6
        self.min_readable_ratio = 0.7
    
    def extract_text_with_quality_assessment(self, pdf_path: str) -> Dict[int, ExtractionResult]:
        """
        Extract text from PDF using multiple methods and select the best quality result for each page.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary mapping page numbers to best extraction results
        """
        self.logger.info(f"Starting enhanced PDF extraction for: {pdf_path}")
        
        # Try all extraction methods
        pymupdf_results = self._extract_with_pymupdf(pdf_path)
        pdfplumber_results = self._extract_with_pdfplumber(pdf_path)
        pypdf2_results = self._extract_with_pypdf2(pdf_path)
        
        # Select best result for each page
        best_results = {}
        all_pages = set(pymupdf_results.keys()) | set(pdfplumber_results.keys()) | set(pypdf2_results.keys())
        
        for page_num in all_pages:
            candidates = []
            
            if page_num in pymupdf_results and pymupdf_results[page_num].success:
                candidates.append(pymupdf_results[page_num])
            if page_num in pdfplumber_results and pdfplumber_results[page_num].success:
                candidates.append(pdfplumber_results[page_num])
            if page_num in pypdf2_results and pypdf2_results[page_num].success:
                candidates.append(pypdf2_results[page_num])
            
            if candidates:
                # Select the result with the highest quality score
                best_result = max(candidates, key=lambda x: x.quality_metrics.quality_score)
                best_results[page_num] = best_result
                
                self.logger.info(f"Page {page_num}: Best method '{best_result.method}' "
                               f"with quality score {best_result.quality_metrics.quality_score:.3f}")
            else:
                self.logger.warning(f"No successful extraction for page {page_num}")
        
        return best_results
    
    def _extract_with_pymupdf(self, pdf_path: str) -> Dict[int, ExtractionResult]:
        """Extract text using PyMuPDF."""
        results = {}
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    text = page.get_text()
                    
                    # Clean and assess quality
                    cleaned_text = self._clean_text(text)
                    quality_metrics = self._assess_text_quality(cleaned_text)
                    
                    results[page_num + 1] = ExtractionResult(
                        text=cleaned_text,
                        page_number=page_num + 1,
                        method="PyMuPDF",
                        quality_metrics=quality_metrics
                    )
                    
                except Exception as e:
                    self.logger.error(f"PyMuPDF extraction failed for page {page_num + 1}: {e}")
                    results[page_num + 1] = ExtractionResult(
                        text="",
                        page_number=page_num + 1,
                        method="PyMuPDF",
                        quality_metrics=TextQualityMetrics(),
                        success=False,
                        error=str(e)
                    )
            
            doc.close()
            
        except Exception as e:
            self.logger.error(f"PyMuPDF failed to open PDF: {e}")
        
        return results
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> Dict[int, ExtractionResult]:
        """Extract text using pdfplumber."""
        results = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text() or ""
                        
                        # Clean and assess quality
                        cleaned_text = self._clean_text(text)
                        quality_metrics = self._assess_text_quality(cleaned_text)
                        
                        results[page_num + 1] = ExtractionResult(
                            text=cleaned_text,
                            page_number=page_num + 1,
                            method="pdfplumber",
                            quality_metrics=quality_metrics
                        )
                        
                    except Exception as e:
                        self.logger.error(f"pdfplumber extraction failed for page {page_num + 1}: {e}")
                        results[page_num + 1] = ExtractionResult(
                            text="",
                            page_number=page_num + 1,
                            method="pdfplumber",
                            quality_metrics=TextQualityMetrics(),
                            success=False,
                            error=str(e)
                        )
                        
        except Exception as e:
            self.logger.error(f"pdfplumber failed to open PDF: {e}")
        
        return results
    
    def _extract_with_pypdf2(self, pdf_path: str) -> Dict[int, ExtractionResult]:
        """Extract text using PyPDF2."""
        results = {}
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        
                        # Clean and assess quality
                        cleaned_text = self._clean_text(text)
                        quality_metrics = self._assess_text_quality(cleaned_text)
                        
                        results[page_num + 1] = ExtractionResult(
                            text=cleaned_text,
                            page_number=page_num + 1,
                            method="PyPDF2",
                            quality_metrics=quality_metrics
                        )
                        
                    except Exception as e:
                        self.logger.error(f"PyPDF2 extraction failed for page {page_num + 1}: {e}")
                        results[page_num + 1] = ExtractionResult(
                            text="",
                            page_number=page_num + 1,
                            method="PyPDF2",
                            quality_metrics=TextQualityMetrics(),
                            success=False,
                            error=str(e)
                        )
                        
        except Exception as e:
            self.logger.error(f"PyPDF2 failed to open PDF: {e}")
        
        return results
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing artifacts and normalizing."""
        if not text:
            return ""
        
        # Remove Unicode artifacts
        text = self.unicode_artifacts_pattern.sub('', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove excessive punctuation repetition
        text = re.sub(r'([.!?]){3,}', r'\1\1', text)
        
        # Clean up common OCR artifacts
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between lowercase and uppercase
        text = re.sub(r'(\w)(\d)', r'\1 \2', text)        # Add space between letters and numbers
        text = re.sub(r'(\d)(\w)', r'\1 \2', text)        # Add space between numbers and letters
        
        return text.strip()
    
    def _assess_text_quality(self, text: str) -> TextQualityMetrics:
        """Assess the quality of extracted text."""
        metrics = TextQualityMetrics()
        
        if not text:
            return metrics
        
        metrics.total_chars = len(text)
        
        # Count Unicode artifacts
        metrics.unicode_artifacts = len(self.unicode_artifacts_pattern.findall(text))
        
        # Count garbled characters
        for pattern in self.garbled_patterns:
            metrics.garbled_chars += len(pattern.findall(text))
        
        # Count readable words (words with at least 2 letters)
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
        metrics.readable_words = len(words)
        
        # Count valid sentences (sentences with at least 3 words)
        sentences = re.split(r'[.!?]+', text)
        metrics.valid_sentences = len([s for s in sentences if len(s.split()) >= 3])
        
        # Calculate quality score
        if metrics.total_chars > 0:
            # Base score from readable word ratio
            readable_ratio = metrics.readable_words / max(len(text.split()), 1)
            
            # Penalty for artifacts
            artifact_penalty = (metrics.unicode_artifacts + metrics.garbled_chars) / metrics.total_chars
            
            # Bonus for valid sentences
            sentence_bonus = min(metrics.valid_sentences / 10, 0.2)  # Max 20% bonus
            
            metrics.quality_score = max(0, readable_ratio - artifact_penalty + sentence_bonus)
        
        return metrics
    
    def extract_book_title(self, pdf_path: str) -> str:
        """Extract book title from PDF metadata and first few pages."""
        title_candidates = []
        
        # Try to get title from metadata
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            if metadata.get('title'):
                title_candidates.append(metadata['title'])
            doc.close()
        except Exception as e:
            self.logger.error(f"Failed to extract metadata: {e}")
        
        # Try to extract from first few pages
        extraction_results = self.extract_text_with_quality_assessment(pdf_path)
        
        for page_num in sorted(extraction_results.keys())[:3]:  # Check first 3 pages
            result = extraction_results[page_num]
            if result.success and result.quality_metrics.quality_score > self.min_quality_score:
                # Look for title patterns
                lines = result.text.split('\n')[:10]  # First 10 lines
                for line in lines:
                    line = line.strip()
                    if len(line) > 5 and len(line) < 100:  # Reasonable title length
                        # Check if it looks like a title (starts with capital, not too many numbers)
                        if line[0].isupper() and len(re.findall(r'\d', line)) < len(line) * 0.3:
                            title_candidates.append(line)
        
        # Select best title candidate
        if title_candidates:
            # Prefer longer, more descriptive titles
            best_title = max(title_candidates, key=lambda x: len(x.split()))
            return best_title
        
        # Fallback to filename
        return Path(pdf_path).stem
    
    def get_extraction_summary(self, results: Dict[int, ExtractionResult]) -> Dict:
        """Get a summary of extraction results."""
        total_pages = len(results)
        successful_pages = len([r for r in results.values() if r.success])
        
        quality_scores = [r.quality_metrics.quality_score for r in results.values() if r.success]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        method_counts = {}
        for result in results.values():
            if result.success:
                method_counts[result.method] = method_counts.get(result.method, 0) + 1
        
        return {
            'total_pages': total_pages,
            'successful_pages': successful_pages,
            'success_rate': successful_pages / total_pages if total_pages > 0 else 0,
            'average_quality_score': avg_quality,
            'method_distribution': method_counts,
            'high_quality_pages': len([r for r in results.values() 
                                     if r.success and r.quality_metrics.quality_score > self.min_quality_score])
        }
