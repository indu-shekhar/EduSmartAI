"""
Flask application configuration module.
Handles environment-specific settings for development and production.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration class with common settings."""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///chat.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 20 * 1024 * 1024))  # 20MB
    UPLOAD_FOLDER = Path(os.getenv('UPLOAD_FOLDER', './app/static/uploads')).resolve()
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx'}
    
    # Vector database settings
    VECTOR_DIR = Path(os.getenv('VECTOR_DIR', './storage')).resolve()
    EMBEDDING_DB = os.getenv('EMBEDDING_DB', 'chromadb')
    
    # Books directory
    BOOKS_DIR = Path(os.getenv('BOOKS_DIR', './books')).resolve()
    
    # AI/LLM settings
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Ensure directories exist
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        directories = [
            cls.UPLOAD_FOLDER,
            cls.VECTOR_DIR,
            cls.BOOKS_DIR
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
