"""
LlamaIndex service for RAG functionality.
Handles vector storage, embedding, and query processing using Gemini.
Enhanced with citation and source tracking capabilities.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
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
    load_index_from_storage,
    Document
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

logger = logging.getLogger(__name__)


class EnhancedCitationData:
    """Container for citation information."""
    
    def __init__(self, book_name: str, page_number: int, source_id: str, 
                 content_preview: str = "", relevance_score: float = 0.0):
        self.book_name = book_name
        self.page_number = page_number
        self.source_id = source_id
        self.content_preview = content_preview
        self.relevance_score = relevance_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'book_name': self.book_name,
            'page_number': self.page_number,
            'source_id': self.source_id,
            'content_preview': self.content_preview,
            'relevance_score': round(self.relevance_score, 3)
        }


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
        
        # Initialize storage context
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        self.index = None
        
        # Load existing index if available
        self._load_or_create_index()
    
    def _setup_llm_and_embedding(self):
        """Setup LLM and embedding models."""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")
        
        # Configure global settings with better parameters
        Settings.llm = Gemini(
            model_name="models/gemini-2.5-flash",
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
                
                # Store client as instance variable for later use
                self.chroma_client = chroma_client
                
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
                
                # Store collection as instance variable for later use
                self.chroma_collection = chroma_collection
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
    
    def _clear_vector_store(self):
        """Clear the vector store for force rebuild."""
        try:
            logger.info("Clearing vector store for force rebuild")
            
            # For ChromaDB, delete and recreate the collection
            if self.embedding_db.lower() == 'chromadb':
                collection_name = "edusmartai_main"
                
                # Delete existing collection if it exists
                try:
                    self.chroma_client.delete_collection(collection_name)
                    logger.info(f"Deleted existing ChromaDB collection: {collection_name}")
                except Exception as e:
                    logger.warning(f"Could not delete collection (may not exist): {e}")
                
                # Create new collection
                self.chroma_collection = self.chroma_client.create_collection(collection_name)
                logger.info(f"Created new ChromaDB collection: {collection_name}")
                
                # Recreate vector store
                self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
                
                # Update storage context
                self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
                
                # Clear any existing index files
                import shutil
                if self.vector_dir.exists():
                    try:
                        # Remove all files in storage directory except chroma.sqlite3
                        for item in self.vector_dir.iterdir():
                            if item.name != "chroma.sqlite3" and item.name != "__pycache__":
                                if item.is_file():
                                    item.unlink()
                                elif item.is_dir():
                                    shutil.rmtree(item)
                        logger.info("Cleared existing index files")
                    except Exception as e:
                        logger.warning(f"Could not clear index files: {e}")
            
            # Reset index to None - will be recreated
            self.index = None
            logger.info("Vector store cleared successfully")
            
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")
            raise
    
    def refresh_index(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Refresh the vector index with documents from books directory (backwards compatibility)."""
        return self._refresh_index_legacy(force_rebuild)
    
    def refresh_index_with_citations(self, enhanced_chunks_data: List[Dict], force_rebuild: bool = False) -> Dict[str, Any]:
        """Refresh index with enhanced citation data."""
        try:
            # Clear existing index if force rebuild
            if force_rebuild:
                logger.info("Force rebuild requested - clearing existing index")
                self._clear_vector_store()
            
            if not enhanced_chunks_data:
                return {"status": "error", "message": "No document data provided"}
            
            # Create Documents with enhanced metadata
            documents = []
            total_chunks = 0
            
            for file_data in enhanced_chunks_data:
                book_metadata = file_data['metadata']
                chunks = file_data['chunks']
                
                for chunk in chunks:
                    # Create LlamaIndex Document with enhanced metadata
                    doc = Document(
                        text=chunk.content,
                        metadata={
                            'book_name': chunk.book_name,
                            'page_number': chunk.page_number,
                            'chunk_index': chunk.chunk_index,
                            'source_id': chunk.metadata['source_id'],
                            'content_preview': chunk.metadata['content_preview'],
                            'file_path': book_metadata['file_path'],
                            'author': book_metadata.get('author', 'Unknown'),
                            'total_pages': book_metadata.get('total_pages', 0)
                        }
                    )
                    documents.append(doc)
                    total_chunks += 1
            
            logger.info(f"Creating index from {total_chunks} enhanced chunks from {len(enhanced_chunks_data)} books")
            
            # Create index from documents
            if force_rebuild or not self.index:
                # Create fresh storage context if needed
                if not hasattr(self, 'storage_context') or self.storage_context is None:
                    self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
                
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=self.storage_context,
                    show_progress=True
                )
            else:
                # Add documents to existing index
                for doc in documents:
                    self.index.insert(doc)
            
            # Persist the index
            self.index.storage_context.persist(persist_dir=str(self.vector_dir))
            
            logger.info(f"Successfully created enhanced index with {total_chunks} chunks and citation metadata")
            
            return {
                "status": "success",
                "message": f"Enhanced index created with {total_chunks} chunks from {len(enhanced_chunks_data)} books",
                "total_chunks": total_chunks,
                "total_books": len(enhanced_chunks_data)
            }
            
        except Exception as e:
            logger.error(f"Error refreshing enhanced index: {e}")
            return {
                "status": "error",
                "message": f"Error refreshing enhanced index: {str(e)}"
            }
    
    def _refresh_index_legacy(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Legacy index refresh method for backwards compatibility."""
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
        """Perform a query against the vector index with enhanced citation extraction."""
        try:
            if not self.index:
                return {
                    "response": "Index not available. Please refresh the index first.",
                    "citations": [],
                    "status": "error"
                }
            
            # Create query engine with better settings for more detailed responses
            query_engine = self.index.as_query_engine(
                response_mode="tree_summarize",
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
            logger.info(f"Raw response: {response}")
            
            # Enhanced citation extraction
            enhanced_citations = self._extract_enhanced_citations(response)
            
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
            logger.info(f"Found {len(enhanced_citations)} enhanced citations")
            
            # Provide a more informative response if it's too short
            if not response_text or len(response_text) < 20:
                if enhanced_citations:
                    response_text = f"Based on the documents, here's what I found related to your question about '{question}':\n\n"
                    for i, citation in enumerate(enhanced_citations[:2]):
                        response_text += f"From {citation['book_name']} (Page {citation['page_number']}): {citation['content_preview']}\n\n"
                    response_text += "Would you like me to elaborate on any specific aspect?"
                else:
                    response_text = f"I found some information in the documents, but couldn't generate a detailed response for your question: '{question}'. The documents might not contain enough relevant information, or the question might need to be more specific. Please try rephrasing your question or ask about specific topics covered in the uploaded documents."
            
            logger.info(f"Final response length: {len(response_text)}")
            return {
                "response": response_text,
                "citations": enhanced_citations,
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
    
    def _extract_enhanced_citations(self, response) -> List[Dict[str, Any]]:
        """Extract enhanced citations with book names and page numbers."""
        citations = []
        
        try:
            if hasattr(response, 'source_nodes') and response.source_nodes:
                logger.info(f"Found {len(response.source_nodes)} source nodes")
                
                for i, node in enumerate(response.source_nodes[:5]):  # Limit to top 5
                    try:
                        metadata = getattr(node, 'metadata', {})
                        
                        # Extract enhanced citation information
                        book_name = metadata.get('book_name', f'Document {i+1}')
                        page_number = metadata.get('page_number', 0)
                        source_id = metadata.get('source_id', f'source_{i}')
                        content_preview = metadata.get('content_preview', '')
                        
                        # If no content preview in metadata, create from node text
                        if not content_preview and hasattr(node, 'text'):
                            content_preview = node.text[:150] + "..." if len(node.text) > 150 else node.text
                        
                        # Calculate relevance score from node score
                        relevance_score = getattr(node, 'score', 0.0)
                        if relevance_score == 0.0 and hasattr(node, 'similarity'):
                            relevance_score = getattr(node, 'similarity', 0.0)
                        
                        # Create enhanced citation
                        citation = EnhancedCitationData(
                            book_name=book_name,
                            page_number=page_number,
                            source_id=source_id,
                            content_preview=content_preview,
                            relevance_score=relevance_score
                        )
                        
                        citations.append(citation.to_dict())
                        
                        logger.info(f"Extracted citation: {book_name}, Page {page_number}")
                        
                    except Exception as citation_error:
                        logger.warning(f"Error processing citation {i}: {citation_error}")
                        continue
        
        except Exception as e:
            logger.warning(f"Error extracting enhanced citations: {e}")
        
        # Remove duplicates based on source_id and sort by relevance
        unique_citations = []
        seen_sources = set()
        
        for citation in sorted(citations, key=lambda x: x['relevance_score'], reverse=True):
            source_key = f"{citation['book_name']}_{citation['page_number']}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                unique_citations.append(citation)
        
        logger.info(f"Returning {len(unique_citations)} unique citations")
        return unique_citations[:3]  # Return top 3 unique citations
    
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
