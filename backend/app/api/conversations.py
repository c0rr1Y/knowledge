"""Conversation CRUD API — list, create, delete, get messages."""

import json
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, ConversationMessage
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConvResponse(BaseModel):
    id: str
    title: str
    knowledge_base_id: str | None = None
    message_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources_json: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[ConvResponse])
def list_conversations(kb_id: str | None = Query(None),
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """List conversations for the current user, scoped to a KB or agent mode."""
    q = db.query(Conversation).filter(Conversation.user_id == current_user.id)
    if kb_id == "agent":
        q = q.filter(Conversation.knowledge_base_id.is_(None))
    elif kb_id:
        q = q.filter(Conversation.knowledge_base_id == kb_id)
    convs = q.order_by(Conversation.updated_at.desc()).all()
    return [
        ConvResponse(
            id=c.id,
            title=c.title,
            knowledge_base_id=c.knowledge_base_id,
            message_count=len(c.messages),
            created_at=c.created_at.isoformat() if c.created_at else "",
            updated_at=c.updated_at.isoformat() if c.updated_at else "",
        )
        for c in convs
    ]


@router.post("", response_model=ConvResponse)
def create_conversation(kb_id: str | None = None,
                        title: str = "新对话",
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    """Create a new conversation, optionally tied to a knowledge base."""
    conv = Conversation(
        user_id=current_user.id,
        knowledge_base_id=kb_id,
        title=title,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConvResponse(
        id=conv.id,
        title=conv.title,
        knowledge_base_id=conv.knowledge_base_id,
        message_count=0,
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
    )


@router.get("/{conv_id}/messages", response_model=list[MessageResponse])
def get_messages(conv_id: str, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    """Get all messages in a conversation."""
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            sources_json=m.sources_json,
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in conv.messages
    ]


@router.delete("/{conv_id}")
def delete_conversation(conv_id: str, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    """Delete a conversation."""
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"message": "Deleted"}


def save_message(conv_id: str, user_id: str, role: str, content: str, sources: list[dict] | None = None) -> str:
    """Save a message to a conversation. Returns the message ID."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        msg = ConversationMessage(
            conversation_id=conv_id,
            role=role,
            content=content,
            sources_json=json.dumps(sources or [], ensure_ascii=False),
        )
        db.add(msg)
        # Update conversation updated_at
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if conv:
            conv.updated_at = msg.created_at
            # Auto-title from first user message
            if role == "user" and conv.title == "新对话":
                conv.title = content[:40] + ("..." if len(content) > 40 else "")
        db.commit()
        return msg.id
    finally:
        db.close()
