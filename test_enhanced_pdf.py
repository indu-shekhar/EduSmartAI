"""
Test script for Enhanced PDF Processor validation.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.enhanced_pdf_processor import EnhancedPDFProcessor

def test_enhanced_pdf_processing():
    """Test the enhanced PDF processor on sample books."""
    processor = EnhancedPDFProcessor()
    
    books_dir = Path("books")
    if not books_dir.exists():
        print("Books directory not found. Please ensure PDF files are in the 'books' folder.")
        return
    
    pdf_files = list(books_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in books directory.")
        return
    
    print(f"Found {len(pdf_files)} PDF files to test")
    print("=" * 60)
    
    for pdf_file in pdf_files:
        print(f"\nTesting: {pdf_file.name}")
        print("-" * 40)
        
        try:
            # Test title extraction
            title = processor.extract_book_title(str(pdf_file))
            print(f"Extracted Title: '{title}'")
            
            # Test text extraction with quality assessment
            results = processor.extract_text_with_quality_assessment(str(pdf_file))
            
            if results:
                summary = processor.get_extraction_summary(results)
                print(f"Pages processed: {summary['successful_pages']}/{summary['total_pages']}")
                print(f"Success rate: {summary['success_rate']:.1%}")
                print(f"Average quality: {summary['average_quality_score']:.3f}")
                print(f"High quality pages: {summary['high_quality_pages']}")
                print(f"Methods used: {summary['method_distribution']}")
                
                # Show sample from first few pages
                sample_pages = sorted(results.keys())[:3]
                for page_num in sample_pages:
                    result = results[page_num]
                    if result.success:
                        preview = result.text[:200].replace('\n', ' ')
                        print(f"  Page {page_num} ({result.method}): {preview}...")
                        print(f"    Quality: {result.quality_metrics.quality_score:.3f}, "
                              f"Artifacts: {result.quality_metrics.unicode_artifacts}, "
                              f"Words: {result.quality_metrics.readable_words}")
            else:
                print("No text extracted from PDF")
                
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")
        
        print("-" * 40)

if __name__ == "__main__":
    test_enhanced_pdf_processing()
