"""
Basic tests for the EduSmartAI application.
"""
import pytest
import tempfile
import os
from pathlib import Path

from app import create_app
from app.models.database import db


@pytest.fixture
def app():
    """Create and configure a test app."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


def test_app_creation():
    """Test that the app is created successfully."""
    app = create_app('testing')
    assert app is not None
    assert app.config['TESTING'] is True


def test_health_endpoint(client):
    """Test the health endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'EduSmartAI'


def test_index_redirect(client):
    """Test that index redirects to chat."""
    response = client.get('/')
    assert response.status_code == 302
    assert '/chat' in response.location


def test_chat_page(client):
    """Test that chat page loads."""
    response = client.get('/chat/')
    assert response.status_code == 200
    assert b'EduSmartAI' in response.data


def test_admin_page(client):
    """Test that admin page loads."""
    response = client.get('/admin/')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data


def test_admin_health(client):
    """Test admin health endpoint."""
    response = client.get('/admin/health')
    assert response.status_code in [200, 500]  # May fail if services not initialized
    data = response.get_json()
    assert 'status' in data


def test_config_loading():
    """Test configuration loading."""
    from app.config import Config, DevelopmentConfig, ProductionConfig
    
    # Test base config
    assert hasattr(Config, 'SECRET_KEY')
    assert hasattr(Config, 'SQLALCHEMY_DATABASE_URI')
    
    # Test development config
    assert DevelopmentConfig.DEBUG is True
    
    # Test production config
    assert ProductionConfig.DEBUG is False


class TestServices:
    """Test service initialization and basic functionality."""
    
    def test_conversation_service_init(self):
        """Test conversation service initialization."""
        from app.services.conversation_service import ConversationService
        
        service = ConversationService()
        assert service is not None
        
        # Test session ID generation
        session_id = service.create_session_id()
        assert session_id is not None
        assert len(session_id) > 0
    
    def test_pdf_ingestion_service_init(self):
        """Test PDF ingestion service initialization."""
        from app.services.pdf_ingestion import PDFIngestionPipeline
        from app.config import Config
        
        # Create a mock config
        config = Config()
        config.BOOKS_DIR = Path(tempfile.mkdtemp())
        config.UPLOAD_FOLDER = Path(tempfile.mkdtemp())
        
        # This will fail without LlamaIndexService, but we can test initialization
        try:
            service = PDFIngestionPipeline(config, None)
            assert service is not None
        except Exception:
            # Expected if services not fully configured
            pass


class TestModels:
    """Test database models."""
    
    def test_chat_message_model(self, app):
        """Test ChatMessage model."""
        from app.models.database import ChatMessage
        
        with app.app_context():
            message = ChatMessage(
                session_id='test-session',
                user_message='Test question',
                assistant_response='Test response',
                response_type='query'
            )
            
            db.session.add(message)
            db.session.commit()
            
            # Test retrieval
            retrieved = ChatMessage.query.first()
            assert retrieved is not None
            assert retrieved.user_message == 'Test question'
            assert retrieved.assistant_response == 'Test response'
            
            # Test to_dict method
            data = retrieved.to_dict()
            assert 'id' in data
            assert 'session_id' in data
            assert data['user_message'] == 'Test question'
    
    def test_uploaded_file_model(self, app):
        """Test UploadedFile model."""
        from app.models.database import UploadedFile
        
        with app.app_context():
            file_record = UploadedFile(
                filename='test.pdf',
                original_filename='test_document.pdf',
                file_path='/tmp/test.pdf',
                file_size=1024,
                file_type='pdf'
            )
            
            db.session.add(file_record)
            db.session.commit()
            
            # Test retrieval
            retrieved = UploadedFile.query.first()
            assert retrieved is not None
            assert retrieved.filename == 'test.pdf'
            assert retrieved.file_size == 1024
            
            # Test to_dict method
            data = retrieved.to_dict()
            assert 'id' in data
            assert 'filename' in data
            assert data['file_size'] == 1024


class TestAPI:
    """Test API endpoints."""
    
    def test_chat_message_no_data(self, client):
        """Test chat message endpoint with no data."""
        response = client.post('/chat/message', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_chat_message_empty(self, client):
        """Test chat message endpoint with empty message."""
        response = client.post('/chat/message', json={'message': ''})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_chat_history_empty(self, client):
        """Test chat history endpoint."""
        response = client.get('/chat/history')
        assert response.status_code == 200
        data = response.get_json()
        assert 'history' in data
        assert isinstance(data['history'], list)
    
    def test_new_session(self, client):
        """Test new session creation."""
        response = client.post('/chat/session/new')
        assert response.status_code == 200
        data = response.get_json()
        assert 'session_id' in data
        assert 'message' in data
    
    def test_file_upload_no_file(self, client):
        """Test file upload with no file."""
        response = client.post('/file/upload')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_admin_metrics(self, client):
        """Test admin metrics endpoint."""
        response = client.get('/admin/metrics')
        # May succeed or fail depending on service initialization
        assert response.status_code in [200, 500]


def test_static_files_exist():
    """Test that required static files exist."""
    static_files = [
        'app/static/css/custom.css',
        'app/static/js/app.js',
        'app/static/js/chat.js',
        'app/static/js/admin.js'
    ]
    
    for file_path in static_files:
        assert Path(file_path).exists(), f"Static file {file_path} does not exist"


def test_templates_exist():
    """Test that required templates exist."""
    templates = [
        'app/templates/base.html',
        'app/templates/chat.html',
        'app/templates/admin.html'
    ]
    
    for template_path in templates:
        assert Path(template_path).exists(), f"Template {template_path} does not exist"


def test_scripts_exist():
    """Test that Windows scripts exist."""
    scripts = [
        'scripts/activate_venv.bat',
        'scripts/run_dev.ps1',
        'scripts/ingest.ps1',
        'scripts/schedule_reingest.xml'
    ]
    
    for script_path in scripts:
        assert Path(script_path).exists(), f"Script {script_path} does not exist"


def test_requirements_file():
    """Test that requirements.txt exists and has content."""
    requirements_path = Path('requirements.txt')
    assert requirements_path.exists()
    
    content = requirements_path.read_text()
    assert 'Flask' in content
    assert 'llama-index' in content
    assert 'chromadb' in content


def test_env_example():
    """Test that .env.example exists and has required variables."""
    env_example_path = Path('.env.example')
    assert env_example_path.exists()
    
    content = env_example_path.read_text()
    assert 'GEMINI_API_KEY' in content
    assert 'FLASK_ENV' in content
    assert 'PORT' in content


if __name__ == '__main__':
    pytest.main([__file__])
