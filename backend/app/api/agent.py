"""Agent API — multi-knowledge-base routing with conversation persistence."""

import json
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.kb_member import KBMember
from app.models.conversation import Conversation, ConversationMessage
from app.middleware.auth import get_current_user
from app.core.embeddings import get_embedding_model
from app.core.vector_store import get_vector_store, get_collection_name
from app.core.llm_client import get_llm_client
from app.core.reranker import rerank
from app.core.hybrid_search import is_statistics_query

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentChatRequest(BaseModel):
    question: str
    history: list[dict] | None = None


def get_user_kbs(db: Session, user_id: str, tenant_id: str) -> list[KnowledgeBase]:
    member_kb_ids = (
        db.query(KBMember.knowledge_base_id)
        .filter(KBMember.user_id == user_id)
        .subquery()
    )
    return db.query(KnowledgeBase).filter(
        KnowledgeBase.tenant_id == tenant_id,
        KnowledgeBase.id.in_(member_kb_ids),
    ).all()


def _search_single_kb(question: str, tenant_id: str, kb_id: str, top_k: int = 5) -> list[dict]:
    from app.core.hybrid_search import hybrid_search
    embedding_model = get_embedding_model()
    vector_store = get_vector_store()
    collection_name = get_collection_name(tenant_id, kb_id)
    return hybrid_search(question, collection_name, vector_store, embedding_model, top_k=top_k)


def _get_or_create_conv(db: Session, conv_id: Optional[str], user_id: str, question: str) -> str:
    if conv_id:
        conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user_id).first()
        if conv:
            return conv.id
    conv = Conversation(user_id=user_id, knowledge_base_id=None, title=question[:40])
    db.add(conv)
    db.commit()
    return conv.id


def _save_msg(db: Session, conv_id: str, role: str, content: str, sources: Optional[list] = None):
    msg = ConversationMessage(
        conversation_id=conv_id, role=role, content=content,
        sources_json=json.dumps(sources or [], ensure_ascii=False))
    db.add(msg)
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if conv and conv.title == "新对话" and role == "user":
        conv.title = content[:40] + ("..." if len(content) > 40 else "")
    db.commit()


@router.post("/chat")
async def agent_chat(
    req: AgentChatRequest,
    request: Request,
    conversation_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kbs = get_user_kbs(db, current_user.id, current_user.tenant_id)
    if not kbs:
        raise HTTPException(status_code=400, detail="No knowledge bases available")

    conv_id = _get_or_create_conv(db, conversation_id, current_user.id, req.question)
    _save_msg(db, conv_id, "user", req.question)

    # Search across all KBs
    is_stats = is_statistics_query(req.question)
    per_kb = 12 if is_stats else 5
    all_chunks = []
    for kb in kbs:
        chunks = _search_single_kb(req.question, current_user.tenant_id, kb.id, top_k=per_kb)
        for chunk in chunks:
            chunk["kb_name"] = kb.name
            chunk["kb_id"] = kb.id
        all_chunks.extend(chunks)

    if all_chunks:
        all_chunks = rerank(req.question, all_chunks, top_k=25 if is_stats else 5)

    context_parts = []
    for i, chunk in enumerate(all_chunks):
        meta = chunk["metadata"]
        kb_name = chunk.get("kb_name", "Unknown")
        context_parts.append(
            f"[来源{i+1}] 知识库: {kb_name} | 文档: {meta.get('filename', 'Unknown')}, "
            f"页码: {meta.get('page', 'N/A')}\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    stats_instruction = (
        "\n\n这是一个统计/汇总类问题：请基于下方提供的所有数据逐条计算，不要遗漏任何行、不要编造数据；"
        "若数据不完整，请明确指出缺少了哪些信息。"
        if is_stats else ""
    )

    system_prompt = f"""你是企业知识库问答助手。请基于下方提供的知识库文档片段回答用户问题，回答要准确。

凡是有知识库依据的内容，在该句末尾标注来源编号 [来源N]（N 对应下方片段编号）。{stats_instruction}

知识库文档片段：\n{context if context else "（无相关内容）"}"""

    messages = [{"role": "system", "content": system_prompt}]
    if req.history:
        messages.extend(req.history)
    messages.append({"role": "user", "content": req.question})

    sources = []
    seen = set()
    for chunk in all_chunks:
        meta = chunk["metadata"]
        key = (chunk.get("kb_name", ""), meta.get("filename", ""), meta.get("page", 0))
        if key not in seen:
            seen.add(key)
            sources.append({
                "kb_name": chunk.get("kb_name", "Unknown"),
                "document_name": meta.get("filename", "Unknown"),
                "page": meta.get("page", 0),
                "text_snippet": chunk["text"][:200] + "...",
            })

    async def event_stream() -> AsyncGenerator[str, None]:
        llm = get_llm_client()
        full_answer = ""

        try:
            async for chunk_text in llm.chat_stream(messages):
                full_answer += chunk_text
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk_text}, ensure_ascii=False)}\n\n"

            # Save assistant message
            from app.database import SessionLocal
            _db = SessionLocal()
            try:
                _save_msg(_db, conv_id, "assistant", full_answer, sources)
            finally:
                _db.close()

            yield f"data: {json.dumps({'type': 'sources', 'content': sources}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': {'conv_id': conv_id}}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
