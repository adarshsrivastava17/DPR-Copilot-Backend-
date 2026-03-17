"""Embedding utilities using OpenAI or sentence-transformers."""
from config import get_settings

settings = get_settings()
_embed_model = None


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    if settings.OPENAI_API_KEY:
        return _openai_embeddings(texts)
    else:
        return _local_embeddings(texts)


def _openai_embeddings(texts: list[str]) -> list[list[float]]:
    """Use OpenAI embedding API."""
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.embeddings.create(
        input=texts,
        model=settings.OPENAI_EMBEDDING_MODEL,
    )
    return [item.embedding for item in response.data]


def _local_embeddings(texts: list[str]) -> list[list[float]]:
    """Fallback: use sentence-transformers for local embeddings."""
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = _embed_model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()
