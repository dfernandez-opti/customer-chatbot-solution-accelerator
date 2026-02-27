#!/usr/bin/env python3
"""
Smoke test: run 10 queries and show top-3 results.
Uses Azure AI Search if configured, else keyword match on seed JSON.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "src"))

from dotenv import load_dotenv

load_dotenv(_project_root / ".env")
load_dotenv(_project_root / "src" / "api" / ".env")

from catalog.normalize import content_for_embedding

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


def keyword_match(query: str, docs: List[Dict[str, Any]], top: int = 3) -> List[Dict[str, Any]]:
    """Simple keyword match: score by number of matching keywords."""
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


def search_azure(query: str, top: int = 3) -> List[Dict[str, Any]]:
    """Search via Azure AI Search if configured."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.search.documents import SearchClient

        endpoint = (
            os.getenv("SEARCH_ENDPOINT")
            or os.getenv("AZURE_SEARCH_ENDPOINT")
            or os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        )
        if not endpoint:
            return []
        if not endpoint.startswith("https://"):
            endpoint = f"https://{endpoint}.search.windows.net"

        index_name = os.getenv("SEARCH_INDEX", "servicios_index")
        credential = DefaultAzureCredential()
        client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=credential,
        )
        results = list(client.search(search_text=query, top=top))
        return [
            {
                "id": r.get("id"),
                "nombre": r.get("nombre"),
                "categoria": r.get("categoria"),
                "score": getattr(r, "@search.score", None),
            }
            for r in results
        ]
    except Exception as e:
        print(f"Azure Search error: {e}")
        return []


def main() -> None:
    seed_path = _project_root / "data" / "servicios_opti_2026_seed.json"
    if not seed_path.exists():
        raise SystemExit(f"Seed not found: {seed_path}")

    with open(seed_path, encoding="utf-8") as f:
        docs = json.load(f)

    use_search = bool(
        os.getenv("SEARCH_ENDPOINT")
        or os.getenv("AZURE_SEARCH_ENDPOINT")
        or os.getenv("AZURE_AI_SEARCH_ENDPOINT")
    )

    mode = "Azure AI Search" if use_search else "Keyword match (seed)"
    print(f"Retrieval smoke test ({mode})\n")
    print("-" * 60)

    passed = 0
    for query in TEST_QUERIES:
        if use_search:
            results = search_azure(query, top=3)
        else:
            results = keyword_match(query, docs, top=3)

        found = len(results) > 0
        if found:
            passed += 1

        print(f"\nQ: {query}")
        print(f"  Found: {len(results)}")
        for i, r in enumerate(results, 1):
            name = r.get("nombre", r.get("id", "?"))
            cat = r.get("categoria", "")
            score = r.get("score", "")
            print(f"  {i}. {name} ({cat}) {score}")

    print("\n" + "-" * 60)
    print(f"Passed: {passed}/{len(TEST_QUERIES)} queries returned top-3 results.")
    if passed >= 10:
        print("All 10 queries found relevant services.")
    else:
        print("Some queries may need more keywords in the seed or Azure Search.")


if __name__ == "__main__":
    main()
