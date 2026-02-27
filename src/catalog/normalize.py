"""Helpers for slug, keywords, and content_for_embedding."""

import hashlib
import re
import unicodedata
from typing import List


def slugify(text: str) -> str:
    """Generate URL-safe slug from text."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-").lower()
    return text[:64]


def make_slug(nombre: str, categoria: str) -> str:
    """Generate slug from nombre and categoria."""
    return slugify(f"{categoria}-{nombre}")


def make_stable_id(nombre: str, categoria: str, version: str = "2026.1") -> str:
    """Generate deterministic stable ID for Cosmos DB."""
    raw = f"{categoria}|{slugify(nombre)}|{version}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:12]
    slug = make_slug(nombre, categoria)
    return f"servicio_{slug}_{h}"


def content_for_embedding(doc: dict) -> str:
    """Concatenate searchable fields for embedding generation."""
    parts: List[str] = []
    for key in ["nombre", "descripcion", "problemas_que_resuelve", "incluye", "beneficios", "tecnologias", "keywords", "faq_examples"]:
        val = doc.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            parts.append(" ".join(str(v) for v in val))
        else:
            parts.append(str(val))
    return "\n".join(parts).strip()


def normalize_keywords(keywords: List[str]) -> List[str]:
    """Remove duplicates and empty strings, keep order."""
    seen = set()
    out: List[str] = []
    for k in keywords:
        k = k.strip()
        if k and k.lower() not in seen:
            seen.add(k.lower())
            out.append(k)
    return out
