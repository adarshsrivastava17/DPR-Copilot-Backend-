"""Document parser package."""
from document_parser.pdf_parser import parse_pdf
from document_parser.docx_parser import parse_docx
from document_parser.xlsx_parser import parse_xlsx
from document_parser.section_extractor import extract_sections

__all__ = ["parse_pdf", "parse_docx", "parse_xlsx", "extract_sections"]
