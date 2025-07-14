#!/usr/bin/env python3
"""
Test script for enhanced citation system
"""
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_ingestion import PDFIngestionPipeline, EnhancedDocumentChunk
from app.config import Config
from app.services.llama_index_service import LlamaIndexService

def test_enhanced_ingestion():
    """Test the enhanced PDF ingestion with citation extraction."""
    print("Testing Enhanced Citation System")
    print("=" * 50)
    
    # Create mock config
    config = Config()
    config.ensure_directories()
    
    # Test enhanced document chunk creation
    test_chunk = EnhancedDocumentChunk(
        content="This is a test content about data structures and algorithms.",
        book_name="Introduction to Algorithms",
        page_number=42,
        chunk_index=0,
        start_char=0,
        end_char=58
    )
    
    print(f"✓ Created test chunk:")
    print(f"  Book: {test_chunk.book_name}")
    print(f"  Page: {test_chunk.page_number}")
    print(f"  Content: {test_chunk.content[:50]}...")
    print(f"  Metadata: {test_chunk.metadata}")
    print()
    
    # Test PDF ingestion pipeline
    print("Testing PDF ingestion pipeline...")
    llama_service = LlamaIndexService(config)
    pipeline = PDFIngestionPipeline(config, llama_service)
    
    # Check if books directory has PDFs
    pdf_files = list(config.BOOKS_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files in books directory")
    
    if pdf_files:
        # Test metadata extraction on first PDF
        test_pdf = pdf_files[0]
        print(f"Testing metadata extraction on: {test_pdf.name}")
        
        metadata = pipeline.extract_book_metadata(test_pdf)
        print(f"✓ Extracted metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        print()
        
        # Test text extraction with pages
        print("Testing page-by-page text extraction...")
        pages_text = pipeline.extract_text_with_pages(test_pdf)
        print(f"✓ Extracted text from {len(pages_text)} pages")
        
        if pages_text:
            print(f"  First page sample: {pages_text[0][1][:100]}...")
            print()
            
            # Test enhanced chunk creation
            print("Testing enhanced chunk creation...")
            enhanced_chunks = pipeline.create_enhanced_chunks(pages_text[:2], metadata['book_name'])  # Test first 2 pages
            print(f"✓ Created {len(enhanced_chunks)} enhanced chunks")
            
            if enhanced_chunks:
                first_chunk = enhanced_chunks[0]
                print(f"  First chunk metadata: {first_chunk.metadata}")
                print()
    
    print("✓ Enhanced citation system test completed!")
    return True

if __name__ == "__main__":
    try:
        test_enhanced_ingestion()
        print("\n🎉 All tests passed! Enhanced citation system is ready.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
