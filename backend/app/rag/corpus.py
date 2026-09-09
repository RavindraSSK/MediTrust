"""
Corpus loading: Markdown documents with a small front-matter header.

Each document is split into passages on blank lines. Passages inherit the
document metadata so a retrieved passage can always be cited.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
LIST_KEYS = {"features", "tags"}


@dataclass
class Passage:
    id: str
    doc_id: str
    order: int
    text: str
    title: str
    source: str
    organization: str
    year: int | None
    url: str
    features: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    evidence_type: str = ""

    @property
    def citation(self) -> str:
        parts = [self.source]
        if self.organization:
            parts.append(self.organization)
        if self.year:
            parts.append(str(self.year))
        return ", ".join(parts)

    def to_dict(self, include_text: bool = True) -> dict:
        data = {
            "passage_id": self.id,
            "doc_id": self.doc_id,
            "title": self.title,
            "source": self.source,
            "organization": self.organization,
            "year": self.year,
            "url": self.url,
            "features": list(self.features),
            "tags": list(self.tags),
            "evidence_type": self.evidence_type,
        }
        if include_text:
            data["text"] = self.text
        return data


@dataclass
class Document:
    id: str
    title: str
    source: str
    organization: str
    year: int | None
    url: str
    features: list[str]
    tags: list[str]
    evidence_type: str
    passages: list[Passage]
    path: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "organization": self.organization,
            "year": self.year,
            "url": self.url,
            "features": list(self.features),
            "tags": list(self.tags),
            "evidence_type": self.evidence_type,
            "passages": len(self.passages),
        }


def _parse_front_matter(raw: str) -> dict:
    meta: dict = {}
    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key in LIST_KEYS:
            value = value.strip("[]")
            meta[key] = [item.strip().strip("'\"") for item in value.split(",") if item.strip()]
        elif key == "year":
            try:
                meta[key] = int(value)
            except ValueError:
                meta[key] = None
        else:
            meta[key] = value.strip("'\"")
    return meta


def parse_document(text: str, fallback_id: str, path: str = "") -> Document:
    match = FRONT_MATTER_RE.match(text.strip())
    if match:
        meta = _parse_front_matter(match.group(1))
        body = match.group(2)
    else:
        meta, body = {}, text

    doc_id = str(meta.get("id") or fallback_id)
    title = str(meta.get("title") or fallback_id.replace("_", " ").title())
    source = str(meta.get("source") or title)
    organization = str(meta.get("organization") or "")
    year = meta.get("year")
    url = str(meta.get("url") or "")
    features = list(meta.get("features") or [])
    tags = list(meta.get("tags") or [])
    evidence_type = str(meta.get("evidence_type") or "")

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
    passages = [
        Passage(
            id=f"{doc_id}#{index}",
            doc_id=doc_id,
            order=index,
            text=re.sub(r"\s+", " ", paragraph),
            title=title,
            source=source,
            organization=organization,
            year=year,
            url=url,
            features=features,
            tags=tags,
            evidence_type=evidence_type,
        )
        for index, paragraph in enumerate(paragraphs, start=1)
    ]
    return Document(
        id=doc_id,
        title=title,
        source=source,
        organization=organization,
        year=year,
        url=url,
        features=features,
        tags=tags,
        evidence_type=evidence_type,
        passages=passages,
        path=path,
    )


def load_corpus(corpus_dir: Path | str) -> list[Document]:
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.exists():
        raise FileNotFoundError(f"RAG corpus directory not found: {corpus_dir}")

    documents: list[Document] = []
    seen: set[str] = set()
    for path in sorted(corpus_dir.glob("*.md")):
        document = parse_document(path.read_text(encoding="utf-8"), fallback_id=path.stem, path=str(path))
        if document.id in seen:
            raise ValueError(f"Duplicate corpus document id: {document.id} ({path})")
        seen.add(document.id)
        if document.passages:
            documents.append(document)
    if not documents:
        raise ValueError(f"RAG corpus at {corpus_dir} contains no documents")
    return documents
