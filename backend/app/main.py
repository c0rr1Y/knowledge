"""FastAPI main application entry point."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="企业知识库",
        description="Enterprise Knowledge Base — upload documents, ask questions, get answers.",
        version="1.0.0",
    )

    # CORS — allow frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    from app.api.auth import router as auth_router
    from app.api.kb import router as kb_router
    from app.api.upload import router as upload_router
    from app.api.chat import router as chat_router
    from app.api.conversations import router as conv_router

    app.include_router(auth_router)
    app.include_router(kb_router)
    app.include_router(upload_router)
    app.include_router(chat_router)
    app.include_router(conv_router)

    # Agent router
    from app.api.agent import router as agent_router
    app.include_router(agent_router)

    return app


app = create_app()


@app.on_event("startup")
def on_startup():
    # Create data directories
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)

    # Initialize database
    init_db()

    rebuild_bm25_on_startup()

    print(f"  Server running on http://{settings.host}:{settings.port}")
    print(f"  API docs: http://localhost:{settings.port}/docs")


def rebuild_bm25_on_startup():
    """Rebuild BM25 indexes from ChromaDB data on startup."""
    try:
        from app.core.vector_store import get_vector_store
        from app.core.hybrid_search import index_chunks, _bm25_indexes
        vs = get_vector_store()
        collections = vs.list_collections()
        for col in collections:
            print(f"  [BM25] Rebuilding index for collection: {col.name}")
            try:
                data = col.get(include=["documents", "metadatas"])
                chunks = []
                ids = []
                for i, doc in enumerate(data["documents"]):
                    chunks.append({"text": doc, "metadata": data["metadatas"][i] if data["metadatas"] else {}})
                    ids.append(data["ids"][i] if data["ids"] else str(i))
                if chunks:
                    index_chunks(col.name, chunks, ids)
                    print(f"  [BM25] Indexed {len(chunks)} chunks for {col.name}")
            except Exception as e:
                print(f"  [BM25] Failed for {col.name}: {e}")
    except Exception as e:
        print(f"  [BM25] Rebuild skipped: {e}")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
