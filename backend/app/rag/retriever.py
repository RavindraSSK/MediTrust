"""
Hybrid retriever: BM25 + word/char TF-IDF cosine similarity fused with
reciprocal-rank fusion, with an optional dense sentence-embedding channel.

Everything except the optional dense channel relies on scikit-learn and
NumPy only, so the retriever works in every deployment without downloading
models. Set ``RAG_EMBEDDING_MODEL`` (and install ``sentence-transformers``) to
add semantic embeddings as a third ranking channel.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .corpus import Document, Passage

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "such",
    "than",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "to",
    "was",
    "were",
    "which",
    "who",
    "will",
    "with",
    "within",
    "without",
    "when",
    "where",
    "whether",
    "while",
    "also",
    "both",
    "each",
    "more",
    "most",
    "other",
    "over",
    "per",
    "so",
    "some",
    "very",
    "via",
    "not",
    "no",
    "nor",
    "can",
    "may",
    "might",
    "should",
    "would",
    "could",
}
RRF_K = 60.0


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in TOKEN_RE.findall(text.lower()):
        if token in STOPWORDS or len(token) < 2:
            continue
        # Light stemming: plural stripping keeps "vessels" and "vessel" aligned.
        if len(token) > 4 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return tokens


class BM25:
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_len = np.array([len(doc) for doc in documents], dtype=float)
        self.avg_len = float(self.doc_len.mean()) if len(documents) else 0.0
        self.term_freqs = [Counter(doc) for doc in documents]
        df: Counter = Counter()
        for doc in documents:
            df.update(set(doc))
        n = len(documents)
        self.idf = {term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        scores = np.zeros(len(self.term_freqs), dtype=float)
        if not query_tokens or not len(self.term_freqs):
            return scores
        for idx, tf in enumerate(self.term_freqs):
            length_norm = 1 - self.b + self.b * (self.doc_len[idx] / self.avg_len if self.avg_len else 0.0)
            score = 0.0
            for term in query_tokens:
                freq = tf.get(term)
                if not freq:
                    continue
                score += self.idf.get(term, 0.0) * (freq * (self.k1 + 1)) / (freq + self.k1 * length_norm)
            scores[idx] = score
        return scores


class DenseEncoder:
    """Optional sentence-transformers channel. Never required."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # type: ignore

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vectors, dtype=float)


@dataclass
class RetrievalResult:
    passage: Passage
    score: float
    lexical_score: float
    semantic_score: float
    dense_score: float | None
    boosted: bool

    def to_dict(self, include_text: bool = True) -> dict:
        data = self.passage.to_dict(include_text=include_text)
        data.update(
            {
                "score": round(self.score, 6),
                "lexical_score": round(self.lexical_score, 4),
                "semantic_score": round(self.semantic_score, 4),
                "dense_score": round(self.dense_score, 4) if self.dense_score is not None else None,
                "boosted": self.boosted,
            }
        )
        return data


def _ranks(scores: np.ndarray) -> dict[int, int]:
    """Map passage index -> 1-based rank, only for passages with a positive score."""
    order = np.argsort(-scores, kind="stable")
    ranks: dict[int, int] = {}
    rank = 1
    for idx in order:
        if scores[idx] <= 0:
            break
        ranks[int(idx)] = rank
        rank += 1
    return ranks


class HybridRetriever:
    def __init__(self, passages: list[Passage], embedding_model: str | None = None):
        if not passages:
            raise ValueError("Cannot build a retriever without passages")
        self.passages = passages
        texts = [self._indexable_text(p) for p in passages]

        self.bm25 = BM25([tokenize(t) for t in texts])
        self.word_vectorizer = TfidfVectorizer(
            tokenizer=tokenize,
            preprocessor=None,
            lowercase=False,
            token_pattern=None,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.word_matrix = self.word_vectorizer.fit_transform(texts)
        self.char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1)
        self.char_matrix = self.char_vectorizer.fit_transform(texts)

        self.dense: DenseEncoder | None = None
        self.dense_matrix: np.ndarray | None = None
        if embedding_model:
            try:
                self.dense = DenseEncoder(embedding_model)
                self.dense_matrix = self.dense.encode(texts)
                logger.info("Dense embeddings enabled with %s", embedding_model)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Dense embeddings unavailable (%s); using lexical retrieval only", exc)
                self.dense = None

    @classmethod
    def from_documents(cls, documents: list[Document], embedding_model: str | None = None) -> HybridRetriever:
        passages = [p for doc in documents for p in doc.passages]
        retriever = cls(passages, embedding_model=embedding_model)
        retriever.documents = documents
        return retriever

    @staticmethod
    def _indexable_text(passage: Passage) -> str:
        return " ".join([passage.title, " ".join(passage.tags), " ".join(passage.features), passage.text])

    @property
    def backend_name(self) -> str:
        return "bm25+tfidf(word,char)" + (f"+dense({self.dense.model_name})" if self.dense else "")

    def search(
        self,
        query: str,
        top_k: int = 5,
        boost_features: list[str] | None = None,
        feature_boost: float = 0.5,
        exclude_ids: set[str] | None = None,
    ) -> list[RetrievalResult]:
        query = (query or "").strip()
        if not query:
            return []

        bm25_scores = self.bm25.scores(tokenize(query))
        word_scores = (self.word_matrix @ self.word_vectorizer.transform([query]).T).toarray().ravel()
        char_scores = (self.char_matrix @ self.char_vectorizer.transform([query]).T).toarray().ravel()

        channels = [_ranks(bm25_scores), _ranks(word_scores), _ranks(char_scores)]
        dense_scores = None
        if self.dense is not None and self.dense_matrix is not None:
            dense_scores = self.dense_matrix @ self.dense.encode([query])[0]
            channels.append(_ranks(dense_scores))

        fused = np.zeros(len(self.passages), dtype=float)
        for ranks in channels:
            for idx, rank in ranks.items():
                fused[idx] += 1.0 / (RRF_K + rank)

        boost_set = {f.lower() for f in (boost_features or [])}
        boosted_flags = np.zeros(len(self.passages), dtype=bool)
        if boost_set:
            for idx, passage in enumerate(self.passages):
                if boost_set & {f.lower() for f in passage.features}:
                    fused[idx] *= 1.0 + feature_boost
                    boosted_flags[idx] = True

        exclude = exclude_ids or set()
        order = np.argsort(-fused, kind="stable")
        results: list[RetrievalResult] = []
        for idx in order:
            if fused[idx] <= 0:
                break
            passage = self.passages[idx]
            if passage.id in exclude:
                continue
            results.append(
                RetrievalResult(
                    passage=passage,
                    score=float(fused[idx]),
                    lexical_score=float(bm25_scores[idx]),
                    semantic_score=float(max(word_scores[idx], char_scores[idx])),
                    dense_score=float(dense_scores[idx]) if dense_scores is not None else None,
                    boosted=bool(boosted_flags[idx]),
                )
            )
            if len(results) >= top_k:
                break
        return results
