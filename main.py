"""DPR Copilot — FastAPI Application Entry Point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import get_settings
from database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Detailed Project Report generator for business consultancy firms",
    lifespan=lifespan,
)

# CORS — allow all origins for production + dev
# Note: allow_credentials=False because we use Bearer tokens, not cookies.
# Browsers reject credentials=True with origins=["*"].
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for reports and charts
app.mount("/static/reports", StaticFiles(directory=settings.REPORTS_DIR), name="reports")
app.mount("/static/charts", StaticFiles(directory=settings.CHARTS_DIR), name="charts")

# ─── Routers ──────────────────────────────────────────
from auth.router import router as auth_router
from api.projects import router as projects_router
from api.documents import router as documents_router
from api.reports import router as reports_router
from api.export import router as export_router

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(reports_router)
app.include_router(export_router)


# ─── Root Endpoint ────────────────────────────────────
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "message": "Welcome to DPR Copilot API. Visit /docs for interactive documentation.",
    }


# ─── Health Check ─────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database_url_type": "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite",
    }


# ─── Global Exception Handler ────────────────────────
from fastapi import Request
from fastapi.responses import JSONResponse
import traceback as tb

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_detail = f"{type(exc).__name__}: {str(exc)}"
    print(f"[GLOBAL] ❌ Unhandled error: {error_detail}")
    tb.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": error_detail, "type": type(exc).__name__},
    )


# ─── Debug: Test DB ──────────────────────────────────
@app.get("/api/debug/test-db")
async def test_db():
    """Test database connectivity and table existence."""
    from database import get_db, async_session
    try:
        async with async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            row = result.scalar()
            # Check tables
            if "postgresql" in settings.DATABASE_URL:
                tables_result = await session.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
            else:
                tables_result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [r[0] for r in tables_result.fetchall()]
        return {"db": "connected", "test_query": row, "tables": tables}
    except Exception as e:
        return {"db": "error", "error": f"{type(e).__name__}: {str(e)}"}


# ─── Ingestion Endpoint ──────────────────────────────
@app.post("/api/ingest/reference-dprs")
async def ingest_reference_dprs(directory: str = None):
    """Ingest reference DPR files from a directory into the vector store."""
    from vector_store.ingestion import ingest_directory
    import os

    if directory is None:
        # Default: ingest from sample-dpr folder
        directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample-dpr")

    if not os.path.exists(directory):
        return {"error": f"Directory not found: {directory}"}

    results = ingest_directory(directory)
    return {
        "message": f"Ingested {len(results)} reference DPRs",
        "results": results,
    }


@app.post("/api/ingest/parse-document/{document_id}")
async def parse_document(document_id: str):
    """Parse an uploaded document and store extracted text."""
    from sqlalchemy import select
    from database import async_session
    from models.document import Document

    async with async_session() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return {"error": "Document not found"}

        from document_parser.pdf_parser import parse_pdf
        from document_parser.docx_parser import parse_docx
        from document_parser.xlsx_parser import parse_xlsx
        from document_parser.section_extractor import extract_sections
        import json

        try:
            if doc.file_type == "pdf":
                parsed = parse_pdf(doc.file_path)
            elif doc.file_type == "docx":
                parsed = parse_docx(doc.file_path)
            elif doc.file_type == "xlsx":
                parsed = parse_xlsx(doc.file_path)
            else:
                return {"error": f"Unsupported file type: {doc.file_type}"}

            text = parsed.get("text", "")
            sections = extract_sections(text)

            doc.parsed_text = text
            doc.sections_json = json.dumps(sections)
            await db.commit()

            # If reference doc, ingest into vector store
            if doc.is_reference:
                from vector_store.ingestion import ingest_reference_dpr
                ingest_result = ingest_reference_dpr(doc.file_path, str(doc.id))
                return {"message": "Document parsed and ingested", "sections": list(sections.keys()), "ingestion": ingest_result}

            return {"message": "Document parsed", "sections": list(sections.keys()), "text_length": len(text)}
        except Exception as e:
            return {"error": f"Parse failed: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
