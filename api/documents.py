"""Documents API router: upload, list, delete documents."""
import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.user import User
from models.document import Document
from models.project import Project
from auth.dependencies import get_current_user
from config import get_settings

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()

ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx"}


@router.post("/upload/{project_id}")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    is_reference: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify project ownership
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate file type
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {ALLOWED_EXTENSIONS}")

    # Save file
    file_id = str(uuid.uuid4())
    file_dir = os.path.join(settings.UPLOAD_DIR, str(project_id))
    os.makedirs(file_dir, exist_ok=True)
    file_path = os.path.join(file_dir, f"{file_id}.{ext}")

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Create document record
    doc = Document(
        filename=file.filename,
        file_path=file_path,
        file_type=ext,
        file_size=len(content),
        is_reference=is_reference,
        project_id=project.id,
        user_id=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "is_reference": doc.is_reference,
        "created_at": str(doc.created_at),
    }


@router.post("/upload-reference")
async def upload_reference_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a reference DPR for training the RAG system."""
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {ALLOWED_EXTENSIONS}")

    file_id = str(uuid.uuid4())
    file_dir = os.path.join(settings.UPLOAD_DIR, "references")
    os.makedirs(file_dir, exist_ok=True)
    file_path = os.path.join(file_dir, f"{file_id}.{ext}")

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    doc = Document(
        filename=file.filename,
        file_path=file_path,
        file_type=ext,
        file_size=len(content),
        is_reference=True,
        user_id=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "message": "Reference document uploaded. Run ingestion to add to vector store.",
    }


@router.get("/project/{project_id}")
async def list_project_documents(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "is_reference": d.is_reference,
            "created_at": str(d.created_at),
        }
        for d in docs
    ]


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted"}
