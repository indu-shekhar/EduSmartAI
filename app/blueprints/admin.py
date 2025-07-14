"""
Admin blueprint for system administration and monitoring.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from ..services.llama_index_service import LlamaIndexService
from ..services.pdf_ingestion import PDFIngestionPipeline
from ..services.conversation_service import ConversationService
from ..models.database import db, ChatMessage, UploadedFile, IndexingStatus

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Initialize services (will be injected by app factory)
llama_service = None
pdf_pipeline = None
conversation_service = None


def init_admin_services(llama_svc, pdf_svc, conv_svc):
    """Initialize services for this blueprint."""
    global llama_service, pdf_pipeline, conversation_service
    llama_service = llama_svc
    pdf_pipeline = pdf_svc
    conversation_service = conv_svc


@admin_bp.route('/')
def admin_dashboard():
    """Render admin dashboard."""
    return render_template('admin.html')


@admin_bp.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check RAG system
        rag_status = llama_service.get_index_stats()
        
        # Check processing status
        processing_status = pdf_pipeline.get_processing_status()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'rag_system': rag_status.get('status', 'unknown'),
            'processing': processing_status.get('status', 'unknown')
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500


@admin_bp.route('/metrics')
def get_metrics():
    """Get system metrics and statistics."""
    try:
        # Database metrics
        total_messages = ChatMessage.query.count()
        total_files = UploadedFile.query.count()
        recent_messages = ChatMessage.query.filter(
            ChatMessage.timestamp >= datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        ).count()
        
        # Processing metrics
        processing_status = pdf_pipeline.get_processing_status()
        latest_indexing = IndexingStatus.query.order_by(
            IndexingStatus.start_time.desc()
        ).first()
        
        # RAG metrics
        rag_stats = llama_service.get_index_stats()
        
        return jsonify({
            'database_metrics': {
                'total_messages': total_messages,
                'total_files': total_files,
                'messages_today': recent_messages
            },
            'processing_metrics': processing_status,
            'latest_indexing': latest_indexing.to_dict() if latest_indexing else None,
            'rag_metrics': rag_stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'error': 'Failed to get metrics'}), 500


@admin_bp.route('/re-ingest', methods=['POST'])
def trigger_reingestion():
    """Trigger a full re-ingestion of the books directory."""
    try:
        data = request.get_json() or {}
        force_rebuild = data.get('force_rebuild', True)
        
        # Start background ingestion
        result = pdf_pipeline.bulk_process_books_directory()
        
        return jsonify({
            'message': 'Re-ingestion triggered',
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error triggering re-ingestion: {e}")
        return jsonify({'error': 'Failed to trigger re-ingestion'}), 500


@admin_bp.route('/refresh-index', methods=['POST'])
def refresh_vector_index():
    """Refresh the vector index without re-processing files."""
    try:
        data = request.get_json() or {}
        force_rebuild = data.get('force_rebuild', False)
        
        result = llama_service.refresh_index(force_rebuild=force_rebuild)
        
        return jsonify({
            'message': 'Index refresh completed',
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error refreshing index: {e}")
        return jsonify({'error': 'Failed to refresh index'}), 500


@admin_bp.route('/cleanup', methods=['POST'])
def cleanup_system():
    """Perform system cleanup operations."""
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)
        
        # Cleanup old conversations
        conv_cleanup = conversation_service.cleanup_old_conversations(days=days)
        
        # Cleanup old uploads
        file_cleanup = pdf_pipeline.cleanup_old_uploads(days=days)
        
        return jsonify({
            'message': 'Cleanup completed',
            'conversation_cleanup': conv_cleanup,
            'file_cleanup': file_cleanup,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': 'Failed to perform cleanup'}), 500


@admin_bp.route('/logs')
def get_logs():
    """Get recent application logs."""
    try:
        # This would integrate with your logging system
        # For now, return recent indexing operations
        recent_indexing = IndexingStatus.query.order_by(
            IndexingStatus.start_time.desc()
        ).limit(10).all()
        
        logs = [op.to_dict() for op in recent_indexing]
        
        return jsonify({
            'logs': logs,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': 'Failed to get logs'}), 500


@admin_bp.route('/config')
def get_configuration():
    """Get current system configuration (non-sensitive)."""
    try:
        from flask import current_app
        
        config_info = {
            'vector_store_type': current_app.config.get('EMBEDDING_DB', 'chromadb'),
            'vector_dir': str(current_app.config.get('VECTOR_DIR', './storage')),
            'books_dir': str(current_app.config.get('BOOKS_DIR', './books')),
            'upload_dir': str(current_app.config.get('UPLOAD_FOLDER', './app/static/uploads')),
            'max_content_length': current_app.config.get('MAX_CONTENT_LENGTH', 20971520),
            'allowed_extensions': list(current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'txt', 'doc', 'docx'})),
            'debug_mode': current_app.config.get('DEBUG', False),
            'environment': current_app.config.get('FLASK_ENV', 'development')
        }
        
        return jsonify({
            'configuration': config_info,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        return jsonify({'error': 'Failed to get configuration'}), 500


@admin_bp.route('/sessions')
def get_active_sessions():
    """Get information about active chat sessions."""
    try:
        # Get sessions with recent activity (last 24 hours)
        recent_cutoff = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        session_stats = db.session.query(
            ChatMessage.session_id,
            db.func.count(ChatMessage.id).label('message_count'),
            db.func.max(ChatMessage.timestamp).label('last_activity')
        ).filter(
            ChatMessage.timestamp >= recent_cutoff
        ).group_by(
            ChatMessage.session_id
        ).all()
        
        sessions = []
        for session_id, msg_count, last_activity in session_stats:
            sessions.append({
                'session_id': session_id,
                'message_count': msg_count,
                'last_activity': last_activity.isoformat() if last_activity else None
            })
        
        return jsonify({
            'active_sessions': sessions,
            'total_sessions': len(sessions),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return jsonify({'error': 'Failed to get session information'}), 500
