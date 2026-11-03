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

router = APIRouter(prefix="/api/knowledge-bases", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    history: list[dict] | None = None


class SourceInfo(BaseModel):
    document_name: str
    page: int
    chunk_index: int
    text_snippet: str


def get_kb_access(db: Session, kb_id: str, user_id: str) -> Optional[str]:
    member = db.query(KBMember).filter(
        KBMember.knowledge_base_id == kb_id,
        KBMember.user_id == user_id,
    ).first()
    return member.access_level if member else None


def _get_or_create_conv(db: Session, conv_id: Optional[str], user_id: str, kb_id: str, question: str) -> str:
    """Get existing conversation or create a new one. Returns conv_id."""
    if conv_id:
        conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user_id).first()
        if conv:
            return conv.id
    conv = Conversation(user_id=user_id, knowledge_base_id=kb_id, title=question[:40])
    db.add(conv)
    db.commit()
    return conv.id


def _save_user_message(db: Session, conv_id: str, content: str):
    msg = ConversationMessage(conversation_id=conv_id, role="user", content=content)
    db.add(msg)
    # Update title if first message
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if conv and conv.title == "新对话":
        conv.title = content[:40] + ("..." if len(content) > 40 else "")
    db.commit()


def _save_assistant_message(db: Session, conv_id: str, content: str, sources: list):
    msg = ConversationMessage(conversation_id=conv_id, role="assistant", content=content,
                              sources_json=json.dumps(sources, ensure_ascii=False))
    db.add(msg)
    db.commit()


def search_kb(question: str, tenant_id: str, kb_id: str, top_k: int = 10) -> list[dict]:
    from app.core.hybrid_search import hybrid_search
    embedding_model = get_embedding_model()
    vector_store = get_vector_store()
    collection_name = get_collection_name(tenant_id, kb_id)
    return hybrid_search(question, collection_name, vector_store, embedding_model, top_k=top_k)


@router.post("/{kb_id}/chat")
async def chat_with_kb(
    kb_id: str,
    req: ChatRequest,
    request: Request,
    conversation_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == current_user.tenant_id,
    ).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    access = get_kb_access(db, kb_id, current_user.id)
    if not access:
        raise HTTPException(status_code=403, detail="No access to this knowledge base")

    # Get or create conversation
    conv_id = _get_or_create_conv(db, conversation_id, current_user.id, kb_id, req.question)

    # Save user message
    _save_user_message(db, conv_id, req.question)

    # Search — statistics/aggregation queries need a larger window, otherwise the
    # answer is computed from a partial sample (e.g. only some invoice rows).
    is_stats = is_statistics_query(req.question)
    chunks = search_kb(req.question, current_user.tenant_id, kb_id, top_k=60 if is_stats else 30)
    if chunks:
        chunks = rerank(req.question, chunks, top_k=30 if is_stats else 15)

    # Build context
    context_parts = []
    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        context_parts.append(
            f"[来源{i+1}] 文档: {meta.get('filename', 'Unknown')}, "
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
    for chunk in chunks:
        meta = chunk["metadata"]
        key = (meta.get("filename", ""), meta.get("page", 0))
        if key not in seen:
            seen.add(key)
            sources.append(SourceInfo(
                document_name=meta.get("filename", "Unknown"),
                page=meta.get("page", 0),
                chunk_index=meta.get("chunk_index", 0),
                text_snippet=chunk["text"][:200] + "...",
            ))

    async def event_stream() -> AsyncGenerator[str, None]:
        llm = get_llm_client()
        full_answer = ""

        try:
            async for chunk_text in llm.chat_stream(messages):
                full_answer += chunk_text
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk_text}, ensure_ascii=False)}\n\n"

            # Save assistant message
            sources_data = [s.model_dump() for s in sources]
            from app.database import SessionLocal
            _db = SessionLocal()
            try:
                _save_assistant_message(_db, conv_id, full_answer, sources_data)
            finally:
                _db.close()

            yield f"data: {json.dumps({'type': 'sources', 'content': sources_data}, ensure_ascii=False)}\n\n"
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
