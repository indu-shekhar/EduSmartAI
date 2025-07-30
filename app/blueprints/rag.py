"""
RAG blueprint for direct RAG operations and specialized queries.
"""
import time
import logging
from flask import Blueprint, request, jsonify
from ..services.llama_index_service import LlamaIndexService

logger = logging.getLogger(__name__)

rag_bp = Blueprint('rag', __name__, url_prefix='/rag')

# Initialize service (will be injected by app factory)
llama_service = None


def init_rag_service(llama_svc):
    """Initialize service for this blueprint."""
    global llama_service
    llama_service = llama_svc


@rag_bp.route('/query', methods=['POST'])
def query():
    """Handle direct RAG queries."""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'Question is required'}), 400
        
        question = data['question'].strip()
        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400
        
        # Dynamic max_tokens based on question complexity and user preference
        default_max_tokens = 2000
        user_max_tokens = data.get('max_tokens', default_max_tokens)
        
        # Auto-increase tokens for detailed questions
        question_lower = question.lower()
        requires_detailed_response = any(keyword in question_lower for keyword in [
            'explain', 'describe', 'elaborate', 'detail', 'comprehensive', 'compare', 
            'contrast', 'analyze', 'summarize', 'overview', 'how', 'why', 'what are',
            'list', 'steps', 'process', 'method', 'approach', 'differences', 'similarities'
        ])
        
        if requires_detailed_response:
            max_tokens = max(user_max_tokens, 3000)  # Ensure minimum for detailed responses
        else:
            max_tokens = user_max_tokens
        
        start_time = time.time()
        result = llama_service.query(question, max_tokens=max_tokens)
        processing_time = time.time() - start_time
        
        return jsonify({
            'response': result['response'],
            'citations': result.get('citations', []),
            'processing_time': round(processing_time, 2),
            'status': result.get('status', 'success')
        })
        
    except Exception as e:
        logger.error(f"Error processing RAG query: {e}")
        return jsonify({'error': 'Failed to process query'}), 500


@rag_bp.route('/summary', methods=['POST'])
def summary():
    """Generate summary of indexed content."""
    try:
        data = request.get_json() or {}
        topic = data.get('topic', '').strip() or None
        
        start_time = time.time()
        result = llama_service.summarize(topic)
        processing_time = time.time() - start_time
        
        return jsonify({
            'summary': result['response'],
            'topic': topic,
            'citations': result.get('citations', []),
            'processing_time': round(processing_time, 2),
            'status': result.get('status', 'success')
        })
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return jsonify({'error': 'Failed to generate summary'}), 500


@rag_bp.route('/compare', methods=['POST'])
def compare():
    """Compare two concepts using indexed content."""
    try:
        data = request.get_json()
        if not data or 'concept1' not in data or 'concept2' not in data:
            return jsonify({'error': 'Both concept1 and concept2 are required'}), 400
        
        concept1 = data['concept1'].strip()
        concept2 = data['concept2'].strip()
        
        if not concept1 or not concept2:
            return jsonify({'error': 'Concepts cannot be empty'}), 400
        
        start_time = time.time()
        result = llama_service.compare(concept1, concept2)
        processing_time = time.time() - start_time
        
        return jsonify({
            'comparison': result['response'],
            'concept1': concept1,
            'concept2': concept2,
            'citations': result.get('citations', []),
            'processing_time': round(processing_time, 2),
            'status': result.get('status', 'success')
        })
        
    except Exception as e:
        logger.error(f"Error comparing concepts: {e}")
        return jsonify({'error': 'Failed to compare concepts'}), 500


@rag_bp.route('/index/stats')
def index_stats():
    """Get vector index statistics."""
    try:
        stats = llama_service.get_index_stats()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting index stats: {e}")
        return jsonify({'error': 'Failed to get index statistics'}), 500


@rag_bp.route('/index/refresh', methods=['POST'])
def refresh_index():
    """Refresh the vector index."""
    try:
        data = request.get_json() or {}
        force_rebuild = data.get('force_rebuild', False)
        
        result = llama_service.refresh_index(force_rebuild=force_rebuild)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error refreshing index: {e}")
        return jsonify({'error': 'Failed to refresh index'}), 500


@rag_bp.route('/health')
def health_check():
    """Health check for RAG service."""
    try:
        # Test if service is responsive
        test_result = llama_service.get_index_stats()
        
        if test_result.get('status') == 'success':
            return jsonify({
                'status': 'healthy',
                'message': 'RAG service is operational',
                'index_available': True
            })
        else:
            return jsonify({
                'status': 'degraded',
                'message': 'RAG service has issues',
                'index_available': False,
                'details': test_result
            }), 503
            
    except Exception as e:
        logger.error(f"RAG health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'message': 'RAG service is not responding',
            'error': str(e)
        }), 503
