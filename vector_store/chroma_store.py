"""ChromaDB vector store for DPR reference documents."""
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import get_settings

settings = get_settings()

_client = None
_collection = None


def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"description": "DPR reference document sections"},
        )
    return _collection


def add_documents(
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
    embeddings: list[list[float]] | None = None,
):
    """Add documents to the ChromaDB collection."""
    collection = get_collection()
    kwargs = {"ids": ids, "documents": documents, "metadatas": metadatas}
    if embeddings:
        kwargs["embeddings"] = embeddings
    collection.add(**kwargs)


def search(
    query_text: str,
    n_results: int = 5,
    where: dict | None = None,
    query_embedding: list[float] | None = None,
) -> dict:
    """Search the vector store for similar DPR sections."""
    collection = get_collection()
    kwargs = {"n_results": n_results}

    if query_embedding:
        kwargs["query_embeddings"] = [query_embedding]
    else:
        kwargs["query_texts"] = [query_text]

    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)
    return results


def get_collection_count() -> int:
    """Get the number of documents in the collection."""
    collection = get_collection()
    return collection.count()


def delete_collection():
    """Delete and recreate the collection."""
    global _collection
    client = get_chroma_client()
    try:
        client.delete_collection(settings.CHROMA_COLLECTION_NAME)
    except Exception:
        pass
    _collection = None
