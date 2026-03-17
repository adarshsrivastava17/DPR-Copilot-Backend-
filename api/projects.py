"""Projects API router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.user import User
from models.project import Project
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    business_type: Optional[str] = None
    description: Optional[str] = None
    inputs: Optional[dict] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    business_type: Optional[str] = None
    description: Optional[str] = None
    inputs: Optional[dict] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    business_type: str | None
    description: str | None
    status: str
    inputs: dict | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("/", response_model=ProjectResponse)
async def create_project(
    req: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(
        name=req.name,
        business_type=req.business_type,
        description=req.description,
        inputs=req.inputs,
        user_id=current_user.id,
        org_id=current_user.org_id,
    )
    db.add(project)
    await db.flush()
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        business_type=project.business_type,
        description=project.description,
        status=project.status,
        inputs=project.inputs,
        created_at=str(project.created_at),
        updated_at=str(project.updated_at),
    )


@router.get("/")
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc())
    result = await db.execute(query)
    projects = result.scalars().all()
    return [
        ProjectResponse(
            id=str(p.id), name=p.name, business_type=p.business_type,
            description=p.description, status=p.status, inputs=p.inputs,
            created_at=str(p.created_at), updated_at=str(p.updated_at),
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=str(project.id), name=project.name, business_type=project.business_type,
        description=project.description, status=project.status, inputs=project.inputs,
        created_at=str(project.created_at), updated_at=str(project.updated_at),
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    req: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.flush()

    return ProjectResponse(
        id=str(project.id), name=project.name, business_type=project.business_type,
        description=project.description, status=project.status, inputs=project.inputs,
        created_at=str(project.created_at), updated_at=str(project.updated_at),
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    return {"message": "Project deleted"}
