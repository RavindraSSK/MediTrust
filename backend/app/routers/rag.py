"""Transparency endpoints for the retrieval-augmented clinical context."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import settings
from ..models import User
from ..rag import get_clinical_context_service
from ..security import require_clinical_user

router = APIRouter(prefix="/rag", tags=["RAG"])


def _service():
    if not settings.rag_enabled:
        raise HTTPException(status_code=503, detail="The clinical context (RAG) layer is disabled.")
    return get_clinical_context_service()


@router.get("/status")
def rag_status(user: User = Depends(require_clinical_user)):
    service = _service()
    return {"enabled": True, **service.status()}


@router.get("/sources")
def rag_sources(user: User = Depends(require_clinical_user)):
    service = _service()
    documents = getattr(service.retriever, "documents", [])
    return {"count": len(documents), "documents": [doc.to_dict() for doc in documents]}


@router.get("/search")
def rag_search(
    q: str = Query(..., min_length=2, max_length=300),
    k: int = Query(5, ge=1, le=20),
    feature: str | None = Query(default=None, max_length=40),
    user: User = Depends(require_clinical_user),
):
    service = _service()
    features = [feature] if feature else None
    return {"query": q, "results": service.search(q, top_k=k, features=features)}
