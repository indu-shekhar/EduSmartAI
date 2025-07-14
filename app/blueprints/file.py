"""
File upload and management blueprint.
"""
import os
import logging
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, current_app, send_file

from ..models.database import db, UploadedFile
from ..services.pdf_ingestion import PDFIngestionPipeline

logger = logging.getLogger(__name__)

file_bp = Blueprint('file', __name__, url_prefix='/file')

# Initialize service (will be injected by app factory)
pdf_pipeline = None


def init_file_service(pdf_svc):
    """Initialize service for this blueprint."""
    global pdf_pipeline
    pdf_pipeline = pdf_svc


@file_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file uploads."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not _allowed_file(file.filename):
            return jsonify({
                'error': 'File type not allowed. Supported: PDF, TXT, DOC, DOCX'
            }), 400
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Save file
        upload_path = current_app.config['UPLOAD_FOLDER'] / unique_filename
        file.save(str(upload_path))
        
        # Get file info
        file_size = upload_path.stat().st_size
        file_type = _get_file_type(file_extension)
        
        # Create database record
        uploaded_file = UploadedFile(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=str(upload_path),
            file_size=file_size,
            file_type=file_type
        )
        
        db.session.add(uploaded_file)
        db.session.commit()
        
        # Process file if it's a PDF
        processing_result = None
        if file_type == 'pdf':
            processing_result = pdf_pipeline.process_uploaded_file(uploaded_file.id)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'file_id': uploaded_file.id,
            'filename': original_filename,
            'file_size': file_size,
            'file_type': file_type,
            'processing_result': processing_result
        })
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({'error': 'Failed to upload file'}), 500


@file_bp.route('/list')
def list_files():
    """List uploaded files."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        files_query = UploadedFile.query.order_by(
            UploadedFile.upload_timestamp.desc()
        )
        
        files_paginated = files_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        files_list = [file.to_dict() for file in files_paginated.items]
        
        return jsonify({
            'files': files_list,
            'total': files_paginated.total,
            'page': page,
            'per_page': per_page,
            'total_pages': files_paginated.pages
        })
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({'error': 'Failed to list files'}), 500


@file_bp.route('/download/<int:file_id>')
def download_file(file_id):
    """Download a file by ID."""
    try:
        uploaded_file = UploadedFile.query.get_or_404(file_id)
        file_path = Path(uploaded_file.file_path)
        
        if not file_path.exists():
            return jsonify({'error': 'File not found on disk'}), 404
        
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=uploaded_file.original_filename
        )
        
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        return jsonify({'error': 'Failed to download file'}), 500


@file_bp.route('/delete/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete a file by ID."""
    try:
        uploaded_file = UploadedFile.query.get_or_404(file_id)
        file_path = Path(uploaded_file.file_path)
        
        # Delete file from disk
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database
        db.session.delete(uploaded_file)
        db.session.commit()
        
        return jsonify({
            'message': 'File deleted successfully',
            'filename': uploaded_file.original_filename
        })
        
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        return jsonify({'error': 'Failed to delete file'}), 500


@file_bp.route('/process/<int:file_id>', methods=['POST'])
def process_file(file_id):
    """Manually trigger processing of an uploaded file."""
    try:
        result = pdf_pipeline.process_uploaded_file(file_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing file {file_id}: {e}")
        return jsonify({'error': 'Failed to process file'}), 500


@file_bp.route('/status')
def get_processing_status():
    """Get file processing status."""
    try:
        status = pdf_pipeline.get_processing_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        return jsonify({'error': 'Failed to get processing status'}), 500


@file_bp.route('/cleanup', methods=['POST'])
def cleanup_files():
    """Clean up old processed files."""
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)
        
        result = pdf_pipeline.cleanup_old_uploads(days=days)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': 'Failed to cleanup files'}), 500


def _allowed_file(filename):
    """Check if file extension is allowed."""
    if not filename:
        return False
    
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'txt', 'doc', 'docx'})
    file_extension = Path(filename).suffix.lower().lstrip('.')
    
    return file_extension in allowed_extensions


def _get_file_type(file_extension):
    """Get file type from extension."""
    extension_map = {
        '.pdf': 'pdf',
        '.txt': 'text',
        '.doc': 'document',
        '.docx': 'document',
        '.md': 'markdown'
    }
    
    return extension_map.get(file_extension.lower(), 'unknown')
