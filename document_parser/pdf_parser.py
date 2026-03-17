"""PDF parser using PyMuPDF for text and table extraction."""
import fitz  # PyMuPDF
import re


def parse_pdf(file_path: str) -> dict:
    """
    Extract text, tables, and metadata from a PDF file.
    Returns dict with keys: text, pages, tables, metadata
    """
    doc = fitz.open(file_path)
    full_text = []
    tables = []
    page_texts = []

    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        page_texts.append({"page": page_num + 1, "text": text})
        full_text.append(text)

        # Try to extract tables from the page
        page_tables = _extract_tables_from_page(page)
        if page_tables:
            tables.extend([{"page": page_num + 1, "data": t} for t in page_tables])

    metadata = doc.metadata
    doc.close()

    return {
        "text": "\n\n".join(full_text),
        "pages": page_texts,
        "tables": tables,
        "metadata": metadata,
        "page_count": len(page_texts),
    }


def _extract_tables_from_page(page) -> list:
    """
    Heuristic table extraction: find lines with consistent
    tab/space-separated columns.
    """
    text = page.get_text("text")
    lines = text.split("\n")
    tables = []
    current_table = []

    for line in lines:
        # A table row typically has multiple numbers or key-value pairs
        parts = re.split(r"\s{2,}|\t", line.strip())
        if len(parts) >= 2 and any(_looks_like_number(p) for p in parts):
            current_table.append(parts)
        else:
            if len(current_table) >= 2:
                tables.append(current_table)
            current_table = []

    if len(current_table) >= 2:
        tables.append(current_table)

    return tables


def _looks_like_number(s: str) -> bool:
    """Check if a string looks like a number (including currency)."""
    cleaned = re.sub(r"[₹$,\s%]", "", s.strip())
    try:
        float(cleaned)
        return True
    except ValueError:
        return False
