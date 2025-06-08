from typing import List, Optional, Dict, Any
from loguru import logger
import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain.vectorstores.base import VectorStoreRetriever
from chromadb import Client as ChromaClient

from config import get_settings

settings = get_settings()

class VectorStore:
    """Service for managing vector embeddings and similarity search."""
    
    def __init__(self):
        """Initialize the vector store with configuration."""
        self.embedding_function = self._initialize_embeddings()
        self.vector_store = self._initialize_vector_store()
        
        # Ensure persistence directory exists if needed
        if settings.CHROMA_PERSIST_DIRECTORY:
            os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)

    def _initialize_embeddings(self):
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL_NAME,
                model_kwargs={'device': settings.EMBEDDING_DEVICE},
                encode_kwargs={'normalize_embeddings': settings.NORMALIZE_EMBEDDINGS}
            )
            logger.info("Successfully initialized HuggingFace embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace embeddings: {e}")
            raise ConnectionError(f"Could not initialize embeddings: {e}")

    def _initialize_vector_store(self):
        try:
            vector_store = Chroma(
                collection_name=settings.COLLECTION_NAME,
                embedding_function=self.embedding_function,
                persist_directory=settings.CHROMA_PERSIST_DIRECTORY
            )
            logger.info("Successfully initialized Chroma vector store")
            return vector_store
        except Exception as e:
            logger.error(f"Failed to initialize Chroma vector store: {e}")
            raise ConnectionError(f"Could not initialize vector store: {e}")

    def create_retriever(self, documents: list[Document], **kwargs):
        try:
            # Add documents to vector store
            self.vector_store.add_documents(documents)
            
            # Create retriever with default parameters
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "k": settings.RETRIEVER_K,
                    "score_threshold": 0.8  # Default threshold
                }
            )
            
            logger.info(f"Successfully created retriever with {len(documents)} documents")
            return retriever
        except Exception as e:
            logger.error(f"Failed to create retriever: {e}")
            raise ConnectionError(f"Could not create retriever: {e}")

    def search(self, query: str, k: int = 5):
        try:
            results = self.vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Failed to search vector store: {e}")
            raise ConnectionError(f"Could not search vector store: {e}")

    def delete_collection(self):
        try:
            self.vector_store.delete_collection()
            logger.info("Successfully deleted vector store collection")
        except Exception as e:
            logger.error(f"Failed to delete vector store collection: {e}")
            raise ConnectionError(f"Could not delete vector store collection: {e}")

    def get_collection_stats(self):
        try:
            collection = self.vector_store._collection
            return {
                "count": collection.count(),
                "name": collection.name,
                "metadata": collection.metadata
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            raise ConnectionError(f"Could not get collection stats: {e}")

    async def create_embeddings(
        self,
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Create embeddings for a list of texts.
        
        Args:
            texts: List of texts to create embeddings for
            metadata: Optional list of metadata dictionaries
            
        Returns:
            List of embedding IDs
        """
        if not texts:
            logger.warning("No texts provided for embedding creation")
            return []

        try:
            # Create documents with metadata if provided
            documents = [
                Document(page_content=text, metadata=meta or {})
                for text, meta in zip(texts, metadata or [{}] * len(texts))
            ]

            # Add documents to vector store
            if self.vector_store:
                self.vector_store.add_documents(documents)
                
                # Persist if configured
                if settings.CHROMA_PERSIST_DIRECTORY:
                    self.vector_store.persist()
                
                logger.success(f"Created embeddings for {len(texts)} texts")
                return [str(i) for i in range(len(texts))]  # Return placeholder IDs
            else:
                logger.error("Vector store not initialized")
                return []
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            return []

    async def search_similar(
        self,
        query: str,
        k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar texts using the query.
        
        Args:
            query: Search query
            k: Number of results to return (defaults to config value)
            
        Returns:
            List of dictionaries containing similar texts and scores
        """
        if not query:
            logger.warning("Empty query provided for similarity search")
            return []

        try:
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return []

            # Use configured k value if not specified
            k = k or settings.RETRIEVER_K
            
            # Create retriever with search parameters
            retriever = self.vector_store.as_retriever(
                search_kwargs={"k": k}
            )
            
            # Perform search
            results = retriever.get_relevant_documents(query)
            
            # Format results
            formatted_results = [
                {
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "score": 1.0  # Placeholder score
                }
                for doc in results
            ]
            
            logger.success(f"Found {len(formatted_results)} similar texts")
            return formatted_results
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {e}")
            return []

    async def delete_embeddings(self, ids: List[str]) -> bool:
        """
        Delete embeddings by their IDs.
        
        Args:
            ids: List of embedding IDs to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not ids:
            logger.warning("No IDs provided for deletion")
            return False

        try:
            if self.vector_store:
                # Delete documents from vector store
                self.vector_store.delete(ids)
                
                # Persist if configured
                if settings.CHROMA_PERSIST_DIRECTORY:
                    self.vector_store.persist()
                
                logger.success(f"Deleted {len(ids)} embeddings")
                return True
            else:
                logger.error("Vector store not initialized")
                return False
        except Exception as e:
            logger.error(f"Failed to delete embeddings: {e}")
            return False 