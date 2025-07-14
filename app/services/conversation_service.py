"""
Conversation service for managing chat history and context.
"""
import logging
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..models.database import db, ChatMessage

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation history and context."""
    
    def __init__(self):
        """Initialize the conversation service."""
        pass
    
    def create_session_id(self) -> str:
        """Create a new session ID."""
        return str(uuid.uuid4())
    
    def save_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        response_type: str = "query",
        citations: List[Dict] = None,
        processing_time: float = None
    ) -> ChatMessage:
        """Save a conversation exchange to the database."""
        try:
            # Convert citations to JSON string
            citations_json = json.dumps(citations) if citations else None
            
            # Create new chat message
            chat_message = ChatMessage(
                session_id=session_id,
                user_message=user_message,
                assistant_response=assistant_response,
                response_type=response_type,
                citations=citations_json,
                processing_time=processing_time
            )
            
            db.session.add(chat_message)
            db.session.commit()
            
            logger.info(f"Saved conversation for session {session_id}")
            return chat_message
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            db.session.rollback()
            raise
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        try:
            messages = ChatMessage.query.filter_by(
                session_id=session_id
            ).order_by(
                ChatMessage.timestamp.asc()
            ).limit(limit).all()
            
            history = []
            for message in messages:
                message_dict = message.to_dict()
                # Parse citations JSON
                if message.citations:
                    try:
                        message_dict['citations'] = json.loads(message.citations)
                    except json.JSONDecodeError:
                        message_dict['citations'] = []
                else:
                    message_dict['citations'] = []
                
                history.append(message_dict)
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def get_recent_conversations(
        self,
        session_id: str,
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent conversations for context."""
        try:
            messages = ChatMessage.query.filter_by(
                session_id=session_id
            ).order_by(
                ChatMessage.timestamp.desc()
            ).limit(count).all()
            
            # Reverse to get chronological order
            messages.reverse()
            
            context = []
            for message in messages:
                context.append({
                    "user": message.user_message,
                    "assistant": message.assistant_response,
                    "type": message.response_type,
                    "timestamp": message.timestamp.isoformat() if message.timestamp else None
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting recent conversations: {e}")
            return []
    
    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete all messages for a session."""
        try:
            deleted_count = ChatMessage.query.filter_by(
                session_id=session_id
            ).delete()
            
            db.session.commit()
            
            logger.info(f"Deleted {deleted_count} messages for session {session_id}")
            return {
                "status": "success",
                "message": f"Deleted {deleted_count} messages",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            db.session.rollback()
            return {"status": "error", "message": str(e)}
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        try:
            total_messages = ChatMessage.query.filter_by(session_id=session_id).count()
            
            if total_messages == 0:
                return {
                    "status": "success",
                    "total_messages": 0,
                    "message": "No messages in this session"
                }
            
            # Get first and last message timestamps
            first_message = ChatMessage.query.filter_by(
                session_id=session_id
            ).order_by(ChatMessage.timestamp.asc()).first()
            
            last_message = ChatMessage.query.filter_by(
                session_id=session_id
            ).order_by(ChatMessage.timestamp.desc()).first()
            
            # Get response type distribution
            query_count = ChatMessage.query.filter_by(
                session_id=session_id,
                response_type="query"
            ).count()
            
            summary_count = ChatMessage.query.filter_by(
                session_id=session_id,
                response_type="summary"
            ).count()
            
            compare_count = ChatMessage.query.filter_by(
                session_id=session_id,
                response_type="compare"
            ).count()
            
            # Calculate average processing time
            avg_processing_time = db.session.query(
                db.func.avg(ChatMessage.processing_time)
            ).filter(
                ChatMessage.session_id == session_id,
                ChatMessage.processing_time.isnot(None)
            ).scalar()
            
            return {
                "status": "success",
                "total_messages": total_messages,
                "first_message": first_message.timestamp.isoformat() if first_message else None,
                "last_message": last_message.timestamp.isoformat() if last_message else None,
                "response_types": {
                    "query": query_count,
                    "summary": summary_count,
                    "compare": compare_count
                },
                "average_processing_time": round(avg_processing_time, 2) if avg_processing_time else None
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {"status": "error", "message": str(e)}
    
    def search_conversations(
        self,
        session_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search conversations by content."""
        try:
            messages = ChatMessage.query.filter(
                ChatMessage.session_id == session_id,
                db.or_(
                    ChatMessage.user_message.contains(search_term),
                    ChatMessage.assistant_response.contains(search_term)
                )
            ).order_by(
                ChatMessage.timestamp.desc()
            ).limit(limit).all()
            
            results = []
            for message in messages:
                message_dict = message.to_dict()
                # Parse citations JSON
                if message.citations:
                    try:
                        message_dict['citations'] = json.loads(message.citations)
                    except json.JSONDecodeError:
                        message_dict['citations'] = []
                else:
                    message_dict['citations'] = []
                
                results.append(message_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            return []
    
    def cleanup_old_conversations(self, days: int = 30) -> Dict[str, Any]:
        """Clean up conversations older than specified days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = ChatMessage.query.filter(
                ChatMessage.timestamp < cutoff_date
            ).delete()
            
            db.session.commit()
            
            logger.info(f"Cleaned up {deleted_count} old conversation messages")
            return {
                "status": "success",
                "message": f"Cleaned up {deleted_count} old messages",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            logger.error(f"Error during conversation cleanup: {e}")
            db.session.rollback()
            return {"status": "error", "message": str(e)}
