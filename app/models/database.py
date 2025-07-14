"""
Database models for the EduSmartAI application.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ChatMessage(db.Model):
    """Model for storing chat messages and responses."""
    
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    user_message = db.Column(db.Text, nullable=False)
    assistant_response = db.Column(db.Text, nullable=False)
    response_type = db.Column(db.String(50), default='query')  # query, summary, compare
    citations = db.Column(db.Text)  # JSON string of citations
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    processing_time = db.Column(db.Float)  # seconds
    
    def __repr__(self):
        return f'<ChatMessage {self.id}: {self.user_message[:50]}...>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_message': self.user_message,
            'assistant_response': self.assistant_response,
            'response_type': self.response_type,
            'citations': self.citations,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'processing_time': self.processing_time
        }


class UploadedFile(db.Model):
    """Model for tracking uploaded files."""
    
    __tablename__ = 'uploaded_files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    processing_status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<UploadedFile {self.filename}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'upload_timestamp': self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            'processed': self.processed,
            'processing_status': self.processing_status,
            'error_message': self.error_message
        }


class IndexingStatus(db.Model):
    """Model for tracking indexing operations."""
    
    __tablename__ = 'indexing_status'
    
    id = db.Column(db.Integer, primary_key=True)
    operation_type = db.Column(db.String(50), nullable=False)  # full_rebuild, incremental, file_add
    status = db.Column(db.String(50), default='running')  # running, completed, failed
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    files_processed = db.Column(db.Integer, default=0)
    total_files = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<IndexingStatus {self.operation_type}: {self.status}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'operation_type': self.operation_type,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'files_processed': self.files_processed,
            'total_files': self.total_files,
            'error_message': self.error_message
        }
