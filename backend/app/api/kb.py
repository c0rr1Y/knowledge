from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.kb_member import KBMember
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])


class KBCreateRequest(BaseModel):
    name: str
    description: str = ""


class KBMemberAddRequest(BaseModel):
    user_email: str
    access_level: str = "read"  # read / write / admin


class KBMemberResponse(BaseModel):
    user_id: str
    username: str
    email: str
    access_level: str


class KBResponse(BaseModel):
    id: str
    name: str
    description: str
    document_count: int
    created_at: str
    access_level: str | None = None

    class Config:
        from_attributes = True


def get_kb_access_level(db: Session, kb_id: str, user_id: str) -> str | None:
    member = db.query(KBMember).filter(
        KBMember.knowledge_base_id == kb_id,
        KBMember.user_id == user_id,
    ).first()
    return member.access_level if member else None


@router.get("", response_model=list[KBResponse])
def list_kbs(request: Request, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    """List all knowledge bases the user has access to."""
    # Get KBs where user is a member
    member_kb_ids = (
        db.query(KBMember.knowledge_base_id)
        .filter(KBMember.user_id == current_user.id)
        .subquery()
    )
    kbs = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.tenant_id == current_user.tenant_id,
            KnowledgeBase.id.in_(member_kb_ids),
        )
        .all()
    )

    result = []
    for kb in kbs:
        access = get_kb_access_level(db, kb.id, current_user.id)
        result.append(KBResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            document_count=len(kb.documents),
            created_at=kb.created_at.isoformat() if kb.created_at else "",
            access_level=access,
        ))
    return result


@router.post("", response_model=KBResponse)
def create_kb(req: KBCreateRequest, request: Request, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    """Create a new knowledge base."""
    kb = KnowledgeBase(
        tenant_id=current_user.tenant_id,
        name=req.name,
        description=req.description,
        created_by=current_user.id,
    )
    db.add(kb)
    db.flush()

    # Add creator as admin
    db.add(KBMember(
        knowledge_base_id=kb.id,
        user_id=current_user.id,
        access_level="admin",
    ))
    db.commit()

    return KBResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=0,
        created_at=kb.created_at.isoformat() if kb.created_at else "",
        access_level="admin",
    )


@router.delete("/{kb_id}")
def delete_kb(kb_id: str, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    """Delete a knowledge base (admin only)."""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == current_user.tenant_id,
    ).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    access = get_kb_access_level(db, kb_id, current_user.id)
    if access != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete")

    db.delete(kb)
    db.commit()
    return {"message": "Deleted"}


@router.get("/{kb_id}/members", response_model=list[KBMemberResponse])
def list_members(kb_id: str, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    """List members of a knowledge base (admin only)."""
    access = get_kb_access_level(db, kb_id, current_user.id)
    if access != "admin":
        raise HTTPException(status_code=403, detail="Only admin can manage members")

    members = db.query(KBMember).filter(KBMember.knowledge_base_id == kb_id).all()
    result = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        result.append(KBMemberResponse(
            user_id=m.user_id,
            username=user.username if user else "未知",
            email=user.email if user else "",
            access_level=m.access_level,
        ))
    return result


@router.put("/{kb_id}/members")
def add_member(kb_id: str, req: KBMemberAddRequest,
               db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    """Add a member to knowledge base (admin only)."""
    access = get_kb_access_level(db, kb_id, current_user.id)
    if access != "admin":
        raise HTTPException(status_code=403, detail="Only admin can manage members")

    # Find user by email within same tenant
    target_user = db.query(User).filter(
        User.email == req.user_email,
        User.tenant_id == current_user.tenant_id,
    ).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found in this tenant")

    # Check if already a member
    existing = db.query(KBMember).filter(
        KBMember.knowledge_base_id == kb_id,
        KBMember.user_id == target_user.id,
    ).first()
    if existing:
        existing.access_level = req.access_level
    else:
        db.add(KBMember(
            knowledge_base_id=kb_id,
            user_id=target_user.id,
            access_level=req.access_level,
        ))
    db.commit()
    return {"message": "Member added/updated"}
