"""
Retrieval-augmented clinical context for MediTrust.

The RAG layer grounds the narrative shown next to a prediction in a curated
corpus of guideline-derived passages. It is strictly separate from the risk
model: retrieval and generation only ever *read* the model output (probability,
band, SHAP drivers) and can never change it.
"""

from __future__ import annotations

import logging
import threading

from ..config import settings
from ..llm import gemini_client
from .corpus import load_corpus
from .retriever import HybridRetriever
from .service import ClinicalContextService

logger = logging.getLogger(__name__)

_service: ClinicalContextService | None = None
_lock = threading.Lock()


def get_clinical_context_service() -> ClinicalContextService:
    """Lazily build (and cache) the retriever + generation service."""
    global _service
    if _service is not None:
        return _service
    with _lock:
        if _service is None:
            documents = load_corpus(settings.rag_corpus_dir)
            retriever = HybridRetriever.from_documents(documents, embedding_model=settings.rag_embedding_model or None)
            _service = ClinicalContextService(
                retriever=retriever,
                llm=gemini_client,
                use_llm=settings.rag_use_llm,
                top_k=settings.rag_top_k,
            )
            logger.info(
                "RAG index ready: %d documents, %d passages, backend=%s, llm=%s",
                len(documents),
                len(retriever.passages),
                retriever.backend_name,
                "gemini" if (settings.rag_use_llm and gemini_client.available) else "template-only",
            )
    return _service


def reset_clinical_context_service() -> None:
    global _service
    with _lock:
        _service = None


__all__ = ["get_clinical_context_service", "reset_clinical_context_service", "ClinicalContextService"]
