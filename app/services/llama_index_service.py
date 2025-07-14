"""
LlamaIndex service for RAG functionality.
Handles vector storage, embedding, and query processing using Gemini.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import chroma config first to disable telemetry
try:
    from ..chroma_config import *  # This will disable telemetry
except ImportError:
    pass

from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    StorageContext,
    Settings,
    load_index_from_storage
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

logger = logging.getLogger(__name__)


class LlamaIndexService:
    """Service for managing vector storage and RAG queries."""
    
    def __init__(self, config):
        """Initialize the LlamaIndex service."""
        self.config = config
        self.vector_dir = config.VECTOR_DIR
        self.books_dir = config.BOOKS_DIR
        self.embedding_db = config.EMBEDDING_DB
        self.gemini_api_key = config.GEMINI_API_KEY
        
        # Initialize components
        self._setup_llm_and_embedding()
        self._setup_vector_store()
        self.index = None
        
        # Load existing index if available
        self._load_or_create_index()
    
    def _setup_llm_and_embedding(self):
        """Setup LLM and embedding models."""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")
        
        # Configure global settings with better parameters
        Settings.llm = Gemini(
            model_name="models/gemini-1.5-flash",
            api_key=self.gemini_api_key,
            temperature=0.7,  # Increased for more creative responses
            max_tokens=1024   # Increased token limit
        )
        
        Settings.embed_model = GeminiEmbedding(
            model_name="models/embedding-001",
            api_key=self.gemini_api_key
        )
        
        # Configure text splitter with better settings
        Settings.node_parser = SentenceSplitter(
            chunk_size=512,    # Reduced chunk size for better context
            chunk_overlap=50   # Increased overlap for better continuity
        )
        
        # Set system prompt for better responses
        from llama_index.core import PromptTemplate
        
        qa_prompt_tmpl = (
            "Context information is below.\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "Given the context information and not prior knowledge, "
            "answer the question in a detailed and helpful manner. "
            "If the context doesn't contain enough information to answer the question, "
            "say so explicitly and suggest what kind of information would be needed.\n"
            "Question: {query_str}\n"
            "Answer: "
        )
        
        Settings.text_qa_template = PromptTemplate(qa_prompt_tmpl)
        
        logger.info("LLM and embedding models configured with enhanced settings")
    
    def _setup_vector_store(self):
        """Setup vector store (ChromaDB)."""
        if self.embedding_db.lower() == 'chromadb':
            try:
                # Initialize ChromaDB with telemetry completely disabled
                import chromadb.config
                import os
                
                # Set environment variables to disable telemetry
                os.environ['ANONYMIZED_TELEMETRY'] = 'False'
                os.environ['CHROMA_SERVER_AUTHN_CREDENTIALS_FILE'] = ''
                
                chroma_client = chromadb.PersistentClient(
                    path=str(self.vector_dir),
                    settings=chromadb.config.Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                        is_persistent=True
                    )
                )
                
                # Use a consistent collection name for persistence
                collection_name = "edusmartai_main"
                
                # Try to get existing collection first, create if it doesn't exist
                try:
                    chroma_collection = chroma_client.get_collection(collection_name)
                    logger.info(f"Using existing ChromaDB collection: {collection_name}")
                except:
                    chroma_collection = chroma_client.create_collection(
                        name=collection_name,
                        metadata={"description": "EduSmartAI document collection"}
                    )
                    logger.info(f"Created new ChromaDB collection: {collection_name}")
                
                self.vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
                logger.info(f"ChromaDB vector store initialized at {self.vector_dir}")
                
            except Exception as e:
                logger.error(f"Error setting up ChromaDB: {e}")
                raise ValueError(f"Failed to initialize ChromaDB: {e}")
        else:
            raise ValueError(f"Unsupported embedding database: {self.embedding_db}")
    
    def _load_or_create_index(self):
        """Load existing index or create a new one."""
        try:
            # Try to load existing index
            storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store,
                persist_dir=str(self.vector_dir)
            )
            self.index = load_index_from_storage(storage_context)
            logger.info("Loaded existing vector index")
        except Exception as e:
            logger.warning(f"Could not load existing index: {e}")
            # Create new index
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            self.index = VectorStoreIndex([], storage_context=storage_context)
            logger.info("Created new vector index")
    
    def refresh_index(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Refresh the vector index with documents from books directory."""
        try:
            if force_rebuild:
                # Create fresh index
                storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
                self.index = VectorStoreIndex([], storage_context=storage_context)
                logger.info("Created fresh index for rebuild")
            
            # Load documents
            if not self.books_dir.exists():
                self.books_dir.mkdir(parents=True, exist_ok=True)
                logger.warning(f"Books directory created: {self.books_dir}")
                return {"status": "success", "message": "Books directory created but no files to index"}
            
            documents = SimpleDirectoryReader(
                input_dir=str(self.books_dir),
                recursive=True,
                required_exts=[".pdf", ".txt", ".md", ".docx"]
            ).load_data()
            
            if not documents:
                logger.warning("No documents found in books directory")
                return {"status": "warning", "message": "No documents found to index"}
            
            # Add documents to index
            if force_rebuild:
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=self.index.storage_context
                )
            else:
                for doc in documents:
                    self.index.insert(doc)
            
            # Persist index
            self.index.storage_context.persist(persist_dir=str(self.vector_dir))
            
            logger.info(f"Successfully indexed {len(documents)} documents")
            return {
                "status": "success",
                "message": f"Successfully indexed {len(documents)} documents",
                "document_count": len(documents)
            }
            
        except Exception as e:
            logger.error(f"Error refreshing index: {e}")
            return {
                "status": "error",
                "message": f"Error refreshing index: {str(e)}"
            }
    
    def query(self, question: str, max_tokens: int = 500) -> Dict[str, Any]:
        """Perform a query against the vector index."""
        try:
            if not self.index:
                return {
                    "response": "Index not available. Please refresh the index first.",
                    "citations": [],
                    "status": "error"
                }
            
            # Create query engine with better settings for more detailed responses
            query_engine = self.index.as_query_engine(
                response_mode="tree_summarize",  # Back to tree_summarize for better responses
                similarity_top_k=5,
                verbose=True,
                streaming=False
            )
            
            # Execute query with additional error handling
            logger.info(f"Executing query: {question[:100]}...")
            
            # Try to get a more detailed response by adding context to the question
            enhanced_question = f"Based on the provided documents, please provide a detailed answer to: {question}"
            
            response = query_engine.query(enhanced_question)
            
            # Debug the response object
            logger.info(f"Response object type: {type(response)}")
            logger.info(f"Response object attributes: {dir(response)}")
            logger.info(f"Raw response: {response}")
            
            # Extract citations
            citations = []
            if hasattr(response, 'source_nodes') and response.source_nodes:
                logger.info(f"Found {len(response.source_nodes)} source nodes")
                for i, node in enumerate(response.source_nodes[:5]):  # Increase to 5
                    try:
                        citations.append({
                            "text": node.text[:300] + "..." if len(node.text) > 300 else node.text,
                            "score": getattr(node, 'score', 0.0),
                            "metadata": getattr(node, 'metadata', {}),
                            "source": f"Document {i+1}"
                        })
                    except Exception as citation_error:
                        logger.warning(f"Error processing citation {i}: {citation_error}")
            
            # Process the response more carefully
            response_text = ""
            if hasattr(response, 'response'):
                response_text = str(response.response)
            elif hasattr(response, 'text'):
                response_text = str(response.text)
            else:
                response_text = str(response)
            
            # Clean and validate response
            response_text = response_text.strip()
            
            logger.info(f"Processed response text: '{response_text}'")
            logger.info(f"Response length: {len(response_text)}")
            
            # Provide a more informative response if it's too short
            if not response_text or len(response_text) < 20:
                if citations:
                    response_text = f"Based on the documents, here's what I found related to your question about '{question}':\n\n"
                    for i, citation in enumerate(citations[:2]):
                        response_text += f"From Document {i+1}: {citation['text']}\n\n"
                    response_text += "Would you like me to elaborate on any specific aspect?"
                else:
                    response_text = f"I found some information in the documents, but couldn't generate a detailed response for your question: '{question}'. The documents might not contain enough relevant information, or the question might need to be more specific. Please try rephrasing your question or ask about specific topics covered in the uploaded documents."
            
            logger.info(f"Final response length: {len(response_text)}")
            return {
                "response": response_text,
                "citations": citations,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error during query: {e}", exc_info=True)
            # Provide a more helpful fallback response
            fallback_response = (
                f"I encountered an error while processing your question: '{question}'. "
                "This might be because:\n"
                "1. The documents don't contain relevant information\n"
                "2. The vector database needs to be refreshed\n"
                "3. There's a temporary system issue\n\n"
                "Please try:\n"
                "- Asking a more specific question\n"
                "- Refreshing the document index\n"
                "- Checking if relevant documents are uploaded"
            )
            return {
                "response": fallback_response,
                "citations": [],
                "status": "error"
            }
    
    def summarize(self, topic: str = None) -> Dict[str, Any]:
        """Generate a summary of the indexed content."""
        try:
            if not self.index:
                return {
                    "response": "Index not available. Please refresh the index first.",
                    "citations": [],
                    "status": "error"
                }
            
            if topic:
                query_text = f"Provide a comprehensive summary about {topic} based on the available documents"
            else:
                query_text = "Provide a comprehensive summary of the main topics and concepts covered in the available documents"
            
            return self.query(query_text, max_tokens=800)
            
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
            return {
                "response": f"Error generating summary: {str(e)}",
                "citations": [],
                "status": "error"
            }
    
    def compare(self, concept1: str, concept2: str) -> Dict[str, Any]:
        """Compare two concepts using the indexed content."""
        try:
            if not self.index:
                return {
                    "response": "Index not available. Please refresh the index first.",
                    "citations": [],
                    "status": "error"
                }
            
            query_text = f"Compare and contrast {concept1} and {concept2}. Highlight similarities, differences, and key relationships between these concepts."
            
            return self.query(query_text, max_tokens=800)
            
        except Exception as e:
            logger.error(f"Error during comparison: {e}")
            return {
                "response": f"Error comparing concepts: {str(e)}",
                "citations": [],
                "status": "error"
            }
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index."""
        try:
            if not self.index:
                return {"status": "error", "message": "Index not available"}
            
            # Get document count (approximate)
            stats = {
                "status": "success",
                "vector_store_type": self.embedding_db,
                "storage_directory": str(self.vector_dir),
                "books_directory": str(self.books_dir)
            }
            
            # Try to get more detailed stats if possible
            try:
                if hasattr(self.index, 'docstore') and hasattr(self.index.docstore, 'docs'):
                    stats["document_count"] = len(self.index.docstore.docs)
                if hasattr(self.index, 'vector_store') and hasattr(self.index.vector_store, '_collection'):
                    stats["vector_count"] = self.index.vector_store._collection.count()
            except:
                pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {"status": "error", "message": str(e)}

    def get_index_status(self) -> Dict[str, Any]:
        """Get the current status of the vector index."""
        try:
            if not self.index:
                return {
                    "status": "not_initialized",
                    "message": "Vector index not initialized",
                    "document_count": 0,
                    "collection_info": None
                }
            
            # Try to get collection info
            collection_info = {}
            try:
                if hasattr(self.vector_store, 'chroma_collection'):
                    collection = self.vector_store.chroma_collection
                    collection_info = {
                        "name": collection.name,
                        "count": collection.count() if hasattr(collection, 'count') else 0
                    }
            except Exception as e:
                logger.warning(f"Could not get collection info: {e}")
            
            return {
                "status": "initialized",
                "message": "Vector index is ready",
                "collection_info": collection_info
            }
            
        except Exception as e:
            logger.error(f"Error checking index status: {e}")
            return {
                "status": "error",
                "message": f"Error checking status: {str(e)}",
                "document_count": 0,
                "collection_info": None
            }
