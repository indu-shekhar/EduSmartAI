"""
Chat blueprint for handling chat interactions and conversation management.
"""
import time
import logging
from flask import Blueprint, request, jsonify, session, render_template
from ..services.conversation_service import ConversationService
from ..services.llama_index_service import LlamaIndexService

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

# Initialize services (will be injected by app factory)
conversation_service = None
llama_service = None


def init_chat_services(conv_service, llama_svc):
    """Initialize services for this blueprint."""
    global conversation_service, llama_service
    conversation_service = conv_service
    llama_service = llama_svc


@chat_bp.route('/')
def chat_page():
    """Render the main chat page."""
    # Check if services are initialized
    if conversation_service is None:
        logger.error("Conversation service not initialized")
        return render_template('error.html', 
                             error_message="Service initialization failed. Please check your configuration and try again."), 500
    
    # Create new session if not exists
    if 'session_id' not in session:
        session['session_id'] = conversation_service.create_session_id()
    
    return render_template('chat.html', session_id=session['session_id'])


@chat_bp.route('/message', methods=['POST'])
def send_message():
    """Handle new chat messages."""
    try:
        # Check if services are initialized
        if conversation_service is None or llama_service is None:
            return jsonify({
                'error': 'Services not properly initialized',
                'message': 'Please check your configuration and restart the application.'
            }), 500
        
        # Check index status
        index_status = llama_service.get_index_status()
        if index_status.get('status') == 'not_initialized':
            return jsonify({
                'error': 'Vector index not ready',
                'message': 'Please run document ingestion first to build the search index.',
                'suggestion': 'Run: python ingest.py --refresh'
            }), 503
        
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Get or create session
        if 'session_id' not in session:
            session['session_id'] = conversation_service.create_session_id()
        
        session_id = session['session_id']
        
        # Determine response type based on message content
        response_type = _determine_response_type(user_message)
        
        # Dynamic max_tokens based on message complexity and type
        user_max_tokens = data.get('max_tokens', 2000)
        
        # Auto-increase tokens for detailed questions or specific response types
        message_lower = user_message.lower()
        requires_detailed_response = (
            response_type in ['summary', 'compare'] or
            any(keyword in message_lower for keyword in [
                'explain', 'describe', 'elaborate', 'detail', 'comprehensive', 'compare', 
                'contrast', 'analyze', 'summarize', 'overview', 'how', 'why', 'what are',
                'list', 'steps', 'process', 'method', 'approach', 'differences', 'similarities'
            ])
        )
        
        if requires_detailed_response:
            max_tokens = max(user_max_tokens, 3000)  # Ensure minimum for detailed responses
        else:
            max_tokens = user_max_tokens
        
        # Process message based on type
        start_time = time.time()
        
        if response_type == 'summary':
            # Extract topic if specified
            topic = _extract_topic_from_summary_request(user_message)
            result = llama_service.summarize(topic)
        elif response_type == 'compare':
            # Extract concepts to compare
            concepts = _extract_concepts_from_compare_request(user_message)
            if len(concepts) >= 2:
                result = llama_service.compare(concepts[0], concepts[1])
            else:
                result = llama_service.query(user_message, max_tokens=max_tokens)
        else:
            # Default query with dynamic token sizing
            result = llama_service.query(user_message, max_tokens=max_tokens)
        
        processing_time = time.time() - start_time
        
        # Debug logging
        logger.info(f"Query result: {result}")
        logger.info(f"Response content: '{result.get('response', 'NO_RESPONSE')}'")
        logger.info(f"Response length: {len(str(result.get('response', '')))}")
        
        # Check if response is empty or too short
        response_text = result.get('response', '')
        if not response_text or len(response_text.strip()) < 10:
            logger.warning(f"Short or empty response detected: '{response_text}'")
            response_text = "I apologize, but I couldn't generate a proper response to your question. This might be because the documents don't contain relevant information, or there was an issue processing your query. Please try rephrasing your question or ensure that relevant documents have been uploaded and indexed."
        
        # Save conversation
        chat_message = conversation_service.save_conversation(
            session_id=session_id,
            user_message=user_message,
            assistant_response=response_text,
            response_type=response_type,
            citations=result.get('citations', []),
            processing_time=processing_time
        )
        
        return jsonify({
            'response': response_text,
            'citations': result.get('citations', []),
            'response_type': response_type,
            'message_id': chat_message.id,
            'processing_time': round(processing_time, 2),
            'status': result.get('status', 'success')
        })
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return jsonify({'error': 'Failed to process message'}), 500


@chat_bp.route('/history')
def get_history():
    """Get conversation history for current session."""
    try:
        if 'session_id' not in session:
            return jsonify({'history': []})
        
        limit = request.args.get('limit', 50, type=int)
        history = conversation_service.get_conversation_history(
            session['session_id'], 
            limit=limit
        )
        
        return jsonify({'history': history})
        
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({'error': 'Failed to get conversation history'}), 500


@chat_bp.route('/history/search')
def search_history():
    """Search conversation history."""
    try:
        if 'session_id' not in session:
            return jsonify({'results': []})
        
        search_term = request.args.get('q', '').strip()
        if not search_term:
            return jsonify({'error': 'Search term is required'}), 400
        
        limit = request.args.get('limit', 20, type=int)
        results = conversation_service.search_conversations(
            session['session_id'],
            search_term,
            limit=limit
        )
        
        return jsonify({'results': results})
        
    except Exception as e:
        logger.error(f"Error searching history: {e}")
        return jsonify({'error': 'Failed to search conversation history'}), 500


@chat_bp.route('/session/new', methods=['POST'])
def new_session():
    """Start a new chat session."""
    try:
        if conversation_service is None:
            return jsonify({'error': 'Conversation service not available'}), 500
            
        session['session_id'] = conversation_service.create_session_id()
        return jsonify({
            'session_id': session['session_id'],
            'message': 'New session started'
        })
        
    except Exception as e:
        logger.error(f"Error creating new session: {e}")
        return jsonify({'error': 'Failed to create new session'}), 500


@chat_bp.route('/session/stats')
def get_session_stats():
    """Get statistics for current session."""
    try:
        if 'session_id' not in session:
            return jsonify({'error': 'No active session'}), 400
        
        stats = conversation_service.get_session_stats(session['session_id'])
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting session stats: {e}")
        return jsonify({'error': 'Failed to get session statistics'}), 500


@chat_bp.route('/session/clear', methods=['POST'])
def clear_session():
    """Clear current session history."""
    try:
        if 'session_id' not in session:
            return jsonify({'error': 'No active session'}), 400
        
        result = conversation_service.delete_session(session['session_id'])
        
        # Create new session
        session['session_id'] = conversation_service.create_session_id()
        
        return jsonify({
            'message': 'Session cleared',
            'new_session_id': session['session_id'],
            'deleted_count': result.get('deleted_count', 0)
        })
        
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        return jsonify({'error': 'Failed to clear session'}), 500


def _determine_response_type(message: str) -> str:
    """Determine the type of response needed based on message content."""
    message_lower = message.lower()
    
    # Summary keywords
    summary_keywords = [
        'summarize', 'summary', 'overview', 'main points', 'key concepts',
        'briefly explain', 'give me an overview', 'what are the main'
    ]
    
    # Compare keywords
    compare_keywords = [
        'compare', 'contrast', 'difference', 'differences', 'vs', 'versus',
        'similarities', 'how does', 'what is the difference'
    ]
    
    # Check for summary request
    for keyword in summary_keywords:
        if keyword in message_lower:
            return 'summary'
    
    # Check for comparison request
    for keyword in compare_keywords:
        if keyword in message_lower:
            return 'compare'
    
    # Default to query
    return 'query'


def _extract_topic_from_summary_request(message: str) -> str:
    """Extract topic from summary request."""
    # Simple extraction - look for common patterns
    message_lower = message.lower()
    
    # Patterns like "summarize X" or "give me a summary of X"
    if 'summarize' in message_lower:
        parts = message_lower.split('summarize')
        if len(parts) > 1:
            topic = parts[1].strip()
            # Remove common words
            topic = topic.replace('about', '').replace('the', '').strip()
            return topic
    
    if 'summary of' in message_lower:
        parts = message_lower.split('summary of')
        if len(parts) > 1:
            topic = parts[1].strip()
            return topic
    
    return None


def _extract_concepts_from_compare_request(message: str) -> list:
    """Extract concepts to compare from comparison request."""
    concepts = []
    message_lower = message.lower()
    
    # Look for "vs", "versus", "and" patterns
    if ' vs ' in message_lower:
        parts = message_lower.split(' vs ')
        if len(parts) >= 2:
            concepts.append(parts[0].strip())
            concepts.append(parts[1].strip())
    elif ' versus ' in message_lower:
        parts = message_lower.split(' versus ')
        if len(parts) >= 2:
            concepts.append(parts[0].strip())
            concepts.append(parts[1].strip())
    elif 'compare' in message_lower and ' and ' in message_lower:
        # Pattern like "compare X and Y"
        compare_part = message_lower[message_lower.find('compare'):]
        and_parts = compare_part.split(' and ')
        if len(and_parts) >= 2:
            first = and_parts[0].replace('compare', '').strip()
            second = and_parts[1].strip()
            concepts.append(first)
            concepts.append(second)
    
    return concepts
