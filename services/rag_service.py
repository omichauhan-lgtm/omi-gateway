import os
from abc import ABC, abstractmethod

# DB Setup for specific providers
CHROMADB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")

class AbstractRAGProvider(ABC):
    """
    RAG Interface to explicitly prevent lock-in to any single Vector DB.
    Implementations must support threshold-gated context retrieval.
    """
    @abstractmethod
    def ingest_document(self, doc_id: str, text: str, metadata: dict = None) -> bool:
        pass

    @abstractmethod
    def retrieve_context(self, query: str, top_k: int = 3, threshold: float = 1.2) -> str:
        pass


class ChromaProvider(AbstractRAGProvider):
    """
    Local ChromaDB provider. Ideal for frugal deployments and data sovereignty.
    """
    def __init__(self, collection_name: str = "omi_sovereign_knowledge"):
        import chromadb
        os.makedirs(CHROMADB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMADB_PATH)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def ingest_document(self, doc_id: str, text: str, metadata: dict = None) -> bool:
        meta = metadata or {}
        self.collection.upsert(
            documents=[text],
            metadatas=[meta],
            ids=[doc_id]
        )
        return True

    def retrieve_context(self, query: str, top_k: int = 3, threshold: float = 1.2) -> str:
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            if not results["documents"] or not results["documents"][0]:
                return ""
                
            valid_contexts = []
            documents = results["documents"][0]
            distances = results["distances"][0]
            
            for doc, distance in zip(documents, distances):
                if distance < threshold:
                    valid_contexts.append(doc)
            
            return "\n---\n".join(valid_contexts) if valid_contexts else ""
            
        except Exception:
            # Fallback to empty context on internal vector failure
            return ""

# Provider Factory Switch - Expose only the configured active provider
active_rag_provider: AbstractRAGProvider = ChromaProvider()
rag_engine = active_rag_provider
