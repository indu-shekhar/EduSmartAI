"""
Command-line interface for ingesting documents into the RAG system.
Designed for Windows environment with manual and scheduled execution.
"""
import argparse
import os
import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.config import config, Config
from app.services.llama_index_service import LlamaIndexService
from app.services.pdf_ingestion import PDFIngestionPipeline


def setup_logging(log_level='INFO'):
    """Setup logging for the CLI."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ingest.log')
        ]
    )


def create_mock_config():
    """Create a configuration object for CLI usage."""
    Config.ensure_directories()
    return Config


def main():
    """Main ingestion function."""
    parser = argparse.ArgumentParser(
        description='Ingest documents into EduSmartAI RAG system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest.py --refresh          # Refresh index with current files
  python ingest.py --rebuild          # Completely rebuild the index
  python ingest.py --books ./mybooks  # Use custom books directory
  python ingest.py --verbose          # Enable verbose logging
        """
    )
    
    parser.add_argument(
        '--refresh',
        action='store_true',
        help='Refresh the vector index (default action)'
    )
    
    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Completely rebuild the vector index from scratch'
    )
    
    parser.add_argument(
        '--books',
        type=str,
        help='Path to books directory (default: ./books)'
    )
    
    parser.add_argument(
        '--storage',
        type=str,
        help='Path to storage directory (default: ./storage)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )

    args = parser.parse_args()

    # Setup logging
    log_level = 'DEBUG' if args.verbose else args.log_level
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting EduSmartAI document ingestion...")
        
        # Create configuration
        config_obj = create_mock_config()
        
        # Override paths if provided
        if args.books:
            config_obj.BOOKS_DIR = Path(args.books).resolve()
        if args.storage:
            config_obj.VECTOR_DIR = Path(args.storage).resolve()
        
        logger.info(f"Books directory: {config_obj.BOOKS_DIR}")
        logger.info(f"Storage directory: {config_obj.VECTOR_DIR}")
        
        # Ensure directories exist
        config_obj.BOOKS_DIR.mkdir(parents=True, exist_ok=True)
        config_obj.VECTOR_DIR.mkdir(parents=True, exist_ok=True)
        
        # Check if books directory has any PDFs
        pdf_files = list(config_obj.BOOKS_DIR.glob("*.pdf"))
        if not pdf_files:
            logger.warning(f"No PDF files found in {config_obj.BOOKS_DIR}")
            print(f"\n⚠️  No PDF files found in {config_obj.BOOKS_DIR}")
            print("Please add PDF files to the books directory and run again.")
            return 1
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        print(f"\n📚 Found {len(pdf_files)} PDF files:")
        for pdf_file in pdf_files:
            print(f"  • {pdf_file.name}")
        
        # Initialize services
        logger.info("Initializing services...")
        print("\n🔧 Initializing services...")
        
        # Check for Gemini API key
        if not config_obj.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found in environment")
            print("❌ Error: GEMINI_API_KEY not found in environment variables")
            print("Please set your Gemini API key in the .env file or environment")
            return 1
        
        llama_service = LlamaIndexService(config_obj)
        pdf_pipeline = PDFIngestionPipeline(config_obj, llama_service)
        
        # Create Flask application context for database operations
        app = create_app()
        
        with app.app_context():
            # Determine action
            force_rebuild = args.rebuild
            if not args.refresh and not args.rebuild:
                # Default action is refresh
                force_rebuild = False
            
            action = "Rebuilding" if force_rebuild else "Refreshing"
            logger.info(f"{action} vector index...")
            print(f"\n🚀 {action} vector index...")
            
            # Perform ingestion
            result = pdf_pipeline.bulk_process_books_directory(force_rebuild)
            
            if result['status'] == 'success':
                logger.info(f"Ingestion completed successfully: {result['message']}")
                print(f"\n✅ Success: {result['message']}")
                
                if 'valid_files' in result:
                    print(f"   📄 Processed {result['valid_files']} valid PDFs")
                    print(f"   📊 Total files found: {result['total_files']}")
                
                # Get index statistics
                try:
                    stats = llama_service.get_index_stats()
                    if stats.get('status') == 'success':
                        print(f"\n📈 Index Statistics:")
                        print(f"   • Vector store: {stats.get('vector_store_type', 'Unknown')}")
                        if 'document_count' in stats:
                            print(f"   • Documents: {stats['document_count']}")
                        if 'vector_count' in stats:
                            print(f"   • Vectors: {stats['vector_count']}")
                except Exception as e:
                    logger.warning(f"Could not retrieve index statistics: {e}")
                
                print(f"\n🎯 Ready! You can now start the Flask application and ask questions about your documents.")
                return 0
                
            elif result['status'] == 'warning':
                logger.warning(f"Ingestion completed with warnings: {result['message']}")
                print(f"\n⚠️  Warning: {result['message']}")
                return 0
                
            else:
                logger.error(f"Ingestion failed: {result['message']}")
                print(f"\n❌ Error: {result['message']}")
                return 1
            
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
        print("\n\n⚠️  Ingestion interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")
        print("Check ingest.log for detailed error information")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
