import os
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.document import Document, DocStatus
from app.models.knowledge_base import KnowledgeBase
from app.models.kb_member import KBMember
from app.middleware.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/knowledge-bases", tags=["upload"])


class DocResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size: int
    status: str
    chunk_count: int
    error_message: str
    created_at: str

    class Config:
        from_attributes = True


def get_kb_access(db: Session, kb_id: str, user_id: str) -> str | None:
    member = db.query(KBMember).filter(
        KBMember.knowledge_base_id == kb_id,
        KBMember.user_id == user_id,
    ).first()
    return member.access_level if member else None


@router.post("/{kb_id}/upload", response_model=DocResponse)
async def upload_pdf(
    kb_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF to a knowledge base."""
    # Validate knowledge base
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == current_user.tenant_id,
    ).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Check write permission
    access = get_kb_access(db, kb_id, current_user.id)
    if access not in ("admin", "write"):
        raise HTTPException(status_code=403, detail="No write permission")

    # Validate file type
    ext = os.path.splitext(file.filename)[1].lower()
    from app.core.file_processor import ALLOWED_EXTENSIONS
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Save file
    doc_id = str(uuid.uuid4())
    saved_filename = f"{doc_id}{ext}"

    # Create tenant-specific upload directory
    upload_dir = os.path.join(os.path.abspath(settings.upload_dir), current_user.tenant_id, kb_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, saved_filename)
    # Normalize path to pure Windows backslash format
    file_path = os.path.normpath(file_path)

    content = await file.read()
    file_size = len(content)

    print(f"[Upload] file={file.filename}, size={file_size}, saved_as={saved_filename}, path={file_path}")

    if file_size == 0:
        raise HTTPException(status_code=400, detail=f"File is empty: {file.filename}")

    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    doc = Document(
        id=doc_id,
        knowledge_base_id=kb_id,
        filename=saved_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        status=DocStatus.UPLOADED.value,
        created_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Trigger async processing (fire and forget)
    asyncio.create_task(process_document_async(doc_id, file_path, kb_id, current_user.tenant_id))

    return DocResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message or "",
        created_at=doc.created_at.isoformat() if doc.created_at else "",
    )


async def process_document_async(doc_id: str, file_path: str, kb_id: str, tenant_id: str):
    """Background task: process PDF → chunks → embeddings → ChromaDB."""
    from app.database import SessionLocal
    from app.core.file_processor import process_file
    from app.core.embeddings import get_embedding_model
    from app.core.vector_store import get_vector_store, get_collection_name
    from app.core.hybrid_search import index_chunks, remove_from_index

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return

        # Update status to processing
        doc.status = DocStatus.PROCESSING.value
        db.commit()

        # Parse PDF into chunks
        chunks = process_file(file_path)

        if not chunks:
            doc.status = DocStatus.ERROR.value
            doc.error_message = "No text content extracted from document"
            db.commit()
            return

        # Generate embeddings and store in ChromaDB
        embedding_model = get_embedding_model()
        vector_store = get_vector_store()

        collection_name = get_collection_name(tenant_id, kb_id)
        collection = vector_store.get_or_create_collection(collection_name)

        texts = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                "doc_id": doc_id,
                "chunk_index": chunk["index"],
                "page": chunk.get("page", 0),
                "title": chunk.get("title", ""),
                "filename": doc.original_filename,
            }
            for chunk in chunks
        ]
        ids = [f"{doc_id}_{chunk['index']}" for chunk in chunks]

        # Batch embed and insert
        embeddings = embedding_model.encode(texts, show_progress_bar=False)

        collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

        # Index chunks in BM25 for hybrid search
        chunks_for_index = [{"text": t, "metadata": m} for t, m in zip(texts, metadatas)]
        index_chunks(collection_name, chunks_for_index, ids)

        # Update document status
        doc.status = DocStatus.DONE.value
        doc.chunk_count = len(chunks)
        db.commit()

    except Exception as e:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = DocStatus.ERROR.value
            doc.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.get("/{kb_id}/documents", response_model=list[DocResponse])
def list_documents(kb_id: str, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """List all documents in a knowledge base."""
    docs = db.query(Document).filter(
        Document.knowledge_base_id == kb_id
    ).order_by(Document.created_at.desc()).all()

    return [
        DocResponse(
            id=d.id,
            filename=d.filename,
            original_filename=d.original_filename,
            file_size=d.file_size,
            status=d.status,
            chunk_count=d.chunk_count,
            error_message=d.error_message or "",
            created_at=d.created_at.isoformat() if d.created_at else "",
        )
        for d in docs
    ]


@router.delete("/{kb_id}/documents/{doc_id}")
def delete_document(kb_id: str, doc_id: str, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """Delete a document and its vectors."""
    access = get_kb_access(db, kb_id, current_user.id)
    if access not in ("admin", "write"):
        raise HTTPException(status_code=403, detail="No write permission")

    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.knowledge_base_id == kb_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from ChromaDB
    try:
        from app.core.vector_store import get_vector_store, get_collection_name
        from app.core.hybrid_search import remove_from_index
        vector_store = get_vector_store()
        collection_name = get_collection_name(current_user.tenant_id, kb_id)
        collection = vector_store.get_or_create_collection(collection_name)
        # Delete all chunks for this document
        all_ids = collection.get()["ids"]
        ids_to_delete = [cid for cid in all_ids if cid.startswith(doc_id)]
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
        # Also remove from BM25 index
        remove_from_index(collection_name, doc_id)
    except Exception:
        pass  # Vector cleanup is best-effort

    # Delete file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return {"message": "Deleted"}
