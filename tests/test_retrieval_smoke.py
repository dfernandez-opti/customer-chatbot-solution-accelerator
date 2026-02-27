"""Smoke tests for OPTI services retrieval."""

import json
from pathlib import Path

import pytest

# Add src to path
import sys
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "src"))

from catalog.normalize import content_for_embedding


@pytest.fixture
def seed_docs():
    """Load seed documents."""
    seed_path = _project_root / "data" / "servicios_opti_2026_seed.json"
    if not seed_path.exists():
        pytest.skip("Seed file not found")
    with open(seed_path, encoding="utf-8") as f:
        return json.load(f)


def keyword_match(query: str, docs: list, top: int = 3) -> list:
    """Simple keyword match."""
    q_lower = query.lower()
    q_terms = set(q_lower.split())
    scored = []
    for doc in docs:
        content = content_for_embedding(doc).lower()
        matches = sum(1 for t in q_terms if t in content and len(t) > 2)
        if matches > 0:
            scored.append((matches, doc))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:top]]


TEST_QUERIES = [
    "Tienen SOC?",
    "Implementan Zero Trust?",
    "Que incluye Defender for Cloud?",
    "Tienen Service Desk con catalogo?",
    "Migracion a Azure y gobierno?",
    "Soporte 24/7?",
    "Que servicios de IA operan agentes?",
    "Que es CSP?",
    "Tienen SIEM?",
    "Purview y DLP?",
]


@pytest.mark.parametrize("query", TEST_QUERIES)
def test_query_finds_service_in_top3(query: str, seed_docs: list):
    """Each of the 10 test queries should find at least one service in top-3."""
    results = keyword_match(query, seed_docs, top=3)
    assert len(results) > 0, f"Query '{query}' should return at least 1 result"
    assert len(results) <= 3


def test_seed_has_required_services(seed_docs: list):
    """Seed should contain key services: Seguridad, Sentinel, CSP, IA."""
    nombres = [d.get("nombre", "") for d in seed_docs]
    assert any("Seguridad" in n for n in nombres)
    assert any("Sentinel" in n for n in nombres)
    assert any("CSP" in n or "Cloud Solution" in n for n in nombres)
    assert any("IA" in n or "Inteligencia" in n for n in nombres)


def test_seed_documents_have_required_fields(seed_docs: list):
    """Each document must have id, categoria, nombre, keywords, faq_examples."""
    required = ["id", "categoria", "nombre", "keywords", "faq_examples"]
    for doc in seed_docs:
        for field in required:
            assert field in doc, f"Document {doc.get('id')} missing {field}"
        assert len(doc.get("keywords", [])) >= 10
        assert len(doc.get("faq_examples", [])) >= 5


def test_content_for_embedding_produces_text(seed_docs: list):
    """content_for_embedding should produce non-empty string."""
    for doc in seed_docs:
        content = content_for_embedding(doc)
        assert isinstance(content, str)
        assert len(content) > 20
