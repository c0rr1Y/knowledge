from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.kb_member import KBMember
from app.models.knowledge_base import KnowledgeBase
from app.middleware.auth import create_access_token, get_current_user
from passlib.hash import bcrypt
import uuid

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    tenant_name: Optional[str] = None  # If None, creates a personal tenant


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    user_id: str
    tenant_id: str
    tenant_name: str = ""
    username: str
    email: str
    role: str


class UserInfo(BaseModel):
    user_id: str
    tenant_id: str
    tenant_name: str = ""
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    tenant_name = req.tenant_name or f"{req.username}'s Workspace"

    # Join an existing workspace by name if it already exists, otherwise create one.
    tenant = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    is_joining = tenant is not None

    if not is_joining:
        tenant = Tenant(name=tenant_name, slug=str(uuid.uuid4())[:8])
        db.add(tenant)
        db.flush()

    # The workspace creator is admin; anyone joining an existing workspace is a member.
    user = User(
        tenant_id=tenant.id,
        email=req.email,
        username=req.username,
        hashed_password=bcrypt.hash(req.password),
        role=UserRole.ADMIN.value if not is_joining else UserRole.MEMBER.value,
    )
    db.add(user)
    db.flush()

    if not is_joining:
        # Creator gets a default knowledge base (and is its admin member).
        default_kb = KnowledgeBase(
            tenant_id=tenant.id,
            name="通用知识库",
            description="默认知识库，在这里上传你的文档开始使用",
            created_by=user.id,
        )
        db.add(default_kb)
        db.flush()
        db.add(KBMember(
            knowledge_base_id=default_kb.id,
            user_id=user.id,
            access_level="admin",
        ))

    db.commit()

    token = create_access_token(user.id, tenant.id, user.role)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        username=user.username,
        email=user.email,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not bcrypt.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(user.id, user.tenant_id, user.role)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        tenant_id=user.tenant_id,
        tenant_name=user.tenant.name if user.tenant else "",
        username=user.username,
        email=user.email,
        role=user.role,
    )


@router.get("/me", response_model=UserInfo)
def get_me(current_user: User = Depends(get_current_user)):
    return UserInfo(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        tenant_name=current_user.tenant.name if current_user.tenant else "",
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
    )
