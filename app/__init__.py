"""
Flask application factory and initialization.
"""
import os
import logging
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

from .config import config, Config
from .models import db
from .services import LlamaIndexService, PDFIngestionPipeline, ConversationService


def create_app(config_name=None):
    """Create and configure Flask application."""
    
    # Determine configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Ensure required directories exist
    Config.ensure_directories()
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Configure logging
    _configure_logging(app)
    
    # Initialize services
    services = _initialize_services(app)
    
    # Register blueprints
    _register_blueprints(app, services)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Add some useful template filters and context
    _register_template_helpers(app)
    
    app.logger.info(f"Application created with config: {config_name}")
    
    return app


def _configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        # Production logging setup
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = logging.FileHandler('logs/edusmartai.log')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('EduSmartAI startup')


def _initialize_services(app):
    """Initialize application services."""
    services = {}
    
    try:
        # Create a config object that has the attributes expected by services
        class ServiceConfig:
            def __init__(self, flask_config):
                # Map Flask config to expected attributes
                self.VECTOR_DIR = Path(flask_config.get('VECTOR_DIR', './storage')).resolve()
                self.BOOKS_DIR = Path(flask_config.get('BOOKS_DIR', './books')).resolve()
                self.EMBEDDING_DB = flask_config.get('EMBEDDING_DB', 'chromadb')
                self.GEMINI_API_KEY = flask_config.get('GEMINI_API_KEY')
                self.UPLOAD_FOLDER = Path(flask_config.get('UPLOAD_FOLDER', './app/static/uploads')).resolve()
                
                # Ensure directories exist
                self.VECTOR_DIR.mkdir(parents=True, exist_ok=True)
                self.BOOKS_DIR.mkdir(parents=True, exist_ok=True)
                self.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        
        service_config = ServiceConfig(app.config)
        
        # Initialize LlamaIndex service
        llama_service = LlamaIndexService(service_config)
        services['llama_service'] = llama_service
        app.logger.info("LlamaIndex service initialized")
        
        # Initialize conversation service
        conversation_service = ConversationService()
        services['conversation_service'] = conversation_service
        app.logger.info("Conversation service initialized")
        
        # Initialize PDF ingestion pipeline
        pdf_pipeline = PDFIngestionPipeline(service_config, llama_service)
        services['pdf_pipeline'] = pdf_pipeline
        app.logger.info("PDF ingestion pipeline initialized")
        
    except Exception as e:
        app.logger.error(f"Error initializing services: {e}")
        # In development, we might want to continue without services for testing
        if app.debug:
            app.logger.warning("Continuing in debug mode without full service initialization")
        else:
            raise
    
    return services


def _register_blueprints(app, services):
    """Register Flask blueprints with service injection."""
    from .blueprints import chat_bp, rag_bp, file_bp, admin_bp
    from .blueprints.chat import init_chat_services
    from .blueprints.rag import init_rag_service
    from .blueprints.file import init_file_service
    from .blueprints.admin import init_admin_services
    
    # Initialize blueprint services
    if 'conversation_service' in services and 'llama_service' in services:
        init_chat_services(services['conversation_service'], services['llama_service'])
    
    if 'llama_service' in services:
        init_rag_service(services['llama_service'])
    
    if 'pdf_pipeline' in services:
        init_file_service(services['pdf_pipeline'])
    
    if all(key in services for key in ['llama_service', 'pdf_pipeline', 'conversation_service']):
        init_admin_services(
            services['llama_service'],
            services['pdf_pipeline'],
            services['conversation_service']
        )
    
    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(rag_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(admin_bp)
    
    # Add root route
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('chat.chat_page'))
    
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'EduSmartAI'}


def _register_template_helpers(app):
    """Register template filters and context processors."""
    from datetime import datetime
    import json
    
    @app.template_filter('datetime')
    def datetime_filter(value):
        """Format datetime for templates."""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return value
    
    @app.template_filter('json')
    def json_filter(value):
        """Convert value to JSON for templates."""
        return json.dumps(value)
    
    @app.context_processor
    def inject_config():
        """Inject configuration values into templates."""
        return {
            'app_name': 'EduSmartAI',
            'debug': app.debug
        }
