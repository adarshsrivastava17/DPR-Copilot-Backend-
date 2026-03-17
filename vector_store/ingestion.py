"""Reference DPR ingestion pipeline.

Parses reference DPR files, chunks them by section,
generates embeddings, and stores in ChromaDB.
"""
import os
import uuid
import hashlib
from document_parser.pdf_parser import parse_pdf
from document_parser.docx_parser import parse_docx
from document_parser.section_extractor import extract_sections
from vector_store.chroma_store import add_documents, get_collection_count
from vector_store.embeddings import get_embeddings


def ingest_reference_dpr(file_path: str, doc_id: str | None = None) -> dict:
    """
    Ingest a single reference DPR file into the vector store.
    Returns summary of ingested sections.
    """
    if doc_id is None:
        doc_id = str(uuid.uuid4())

    # Parse the file
    ext = file_path.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        parsed = parse_pdf(file_path)
    elif ext == "docx":
        parsed = parse_docx(file_path)
    else:
        return {"error": f"Unsupported file type: {ext}", "sections": 0}

    text = parsed.get("text", "")
    if not text.strip():
        return {"error": "No text extracted", "sections": 0}

    # Extract sections
    sections = extract_sections(text)

    if not sections:
        # If no sections found, store the full text as one chunk
        sections = {"full_document": text}

    # Prepare chunks for embedding
    ids = []
    documents = []
    metadatas = []

    filename = os.path.basename(file_path)

    for section_key, content in sections.items():
        # Split long sections into smaller chunks (max ~2000 chars)
        chunks = _chunk_text(content, max_chars=2000)
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{doc_id}:{section_key}:{i}".encode()).hexdigest()
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "doc_id": doc_id,
                "filename": filename,
                "section_type": section_key,
                "chunk_index": i,
                "is_reference": True,
            })

    # Generate embeddings and store
    if documents:
        embeddings = get_embeddings(documents)
        add_documents(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "sections_found": list(sections.keys()),
        "total_chunks": len(documents),
        "collection_total": get_collection_count(),
    }


def ingest_directory(directory_path: str) -> list[dict]:
    """Ingest all DPR files in a directory."""
    results = []
    for filename in os.listdir(directory_path):
        if filename.lower().endswith((".pdf", ".docx")):
            file_path = os.path.join(directory_path, filename)
            result = ingest_reference_dpr(file_path)
            results.append(result)
            print(f"  ✓ Ingested: {filename} ({result.get('total_chunks', 0)} chunks)")
    return results


def _chunk_text(text: str, max_chars: int = 2000) -> list[str]:
    """Split text into chunks, trying to break at paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            # If single paragraph is too long, force-split
            if len(para) > max_chars:
                words = para.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= max_chars:
                        current_chunk += word + " "
                    else:
                        chunks.append(current_chunk.strip())
                        current_chunk = word + " "
            else:
                current_chunk = para + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
