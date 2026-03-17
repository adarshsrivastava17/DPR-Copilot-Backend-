"""Authentication router: register, login, me."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from database import get_db
from models.user import User
from models.organization import Organization
from models.subscription import Subscription
from auth.service import hash_password, verify_password, create_access_token
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ─── Schemas ──────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    org_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    org_id: str | None = None
    org_name: str | None = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Routes ───────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create organization if provided
    org = None
    if req.org_name:
        org = Organization(name=req.org_name)
        db.add(org)
        await db.flush()
        # Create default free subscription
        sub = Subscription(org_id=org.id, plan="free", reports_limit=5)
        db.add(sub)

    # Create user
    user = User(
        email=req.email,
        full_name=req.full_name,
        password_hash=hash_password(req.password),
        role="admin" if org else "member",
        org_id=org.id if org else None,
    )
    db.add(user)
    await db.flush()

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            org_id=str(user.org_id) if user.org_id else None,
            org_name=org.name if org else None,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get org name
    org_name = None
    if user.org_id:
        org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
        org = org_result.scalar_one_or_none()
        org_name = org.name if org else None

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            org_id=str(user.org_id) if user.org_id else None,
            org_name=org_name,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    org_name = None
    if current_user.org_id:
        org_result = await db.execute(select(Organization).where(Organization.id == current_user.org_id))
        org = org_result.scalar_one_or_none()
        org_name = org.name if org else None

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        org_id=str(current_user.org_id) if current_user.org_id else None,
        org_name=org_name,
    )
