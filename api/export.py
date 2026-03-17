"""Export API router: PDF and PPTX generation."""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.user import User
from models.report import GeneratedReport
from models.project import Project
from auth.dependencies import get_current_user
from config import get_settings

router = APIRouter(prefix="/api/export", tags=["export"])
settings = get_settings()


@router.post("/{report_id}/pdf")
async def export_pdf(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return a PDF for the given report."""
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report or report.status != "completed":
        raise HTTPException(status_code=404, detail="Report not found or not completed")

    proj_result = await db.execute(select(Project).where(Project.id == report.project_id))
    project = proj_result.scalar_one()

    from export_engine.pdf_generator import generate_pdf
    pdf_path = generate_pdf(
        report_id=str(report.id),
        title=report.title,
        sections=report.sections or {},
        financial_data=report.financial_data or {},
        project_name=project.name,
        business_type=project.business_type or "",
    )

    report.pdf_path = pdf_path
    await db.flush()

    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{report.title}.pdf")


@router.post("/{report_id}/pptx")
async def export_pptx(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return a PowerPoint for the given report."""
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report or report.status != "completed":
        raise HTTPException(status_code=404, detail="Report not found or not completed")

    proj_result = await db.execute(select(Project).where(Project.id == report.project_id))
    project = proj_result.scalar_one()

    from export_engine.pptx_generator import generate_pptx
    pptx_path = generate_pptx(
        report_id=str(report.id),
        title=report.title,
        sections=report.sections or {},
        financial_data=report.financial_data or {},
        project_name=project.name,
    )

    report.pptx_path = pptx_path
    await db.flush()

    return FileResponse(
        pptx_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{report.title}.pptx",
    )
