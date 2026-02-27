#!/usr/bin/env python3
"""
Ingest OPTI services seed to Azure AI Search.
Creates/updates servicios_index with vector search.
Uses env: SEARCH_ENDPOINT, AOAI_ENDPOINT, AOAI_EMBEDDING_DEPLOYMENT, etc.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearch,
    VectorSearchProfile,
)
from dotenv import load_dotenv
from openai import AzureOpenAI

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "src"))

# Cargar .env: raiz del proyecto o src/api (donde la API tambien lee)
load_dotenv(_project_root / ".env")
load_dotenv(_project_root / "src" / "api" / ".env")

from catalog.normalize import content_for_embedding


def get_config() -> Dict[str, str]:
    """Read config from environment."""
    search_endpoint = (
        os.getenv("SEARCH_ENDPOINT")
        or os.getenv("AZURE_SEARCH_ENDPOINT")
        or os.getenv("AZURE_AI_SEARCH_ENDPOINT")
    )
    if not search_endpoint:
        raise SystemExit(
            "Missing SEARCH_ENDPOINT, AZURE_SEARCH_ENDPOINT or AZURE_AI_SEARCH_ENDPOINT."
        )
    if not search_endpoint.startswith("https://"):
        search_endpoint = f"https://{search_endpoint}.search.windows.net"

    aoai_endpoint = (
        os.getenv("AOAI_ENDPOINT")
        or os.getenv("AZURE_OPENAI_ENDPOINT")
        or os.getenv("AZURE_OPENAI_API_BASE")
    )
    if not aoai_endpoint:
        raise SystemExit("Missing AOAI_ENDPOINT or AZURE_OPENAI_ENDPOINT.")

    embedding_deployment = (
        os.getenv("AOAI_EMBEDDING_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")
        or "text-embedding-ada-002"
    )

    index_name = os.getenv("SEARCH_INDEX", "servicios_index")

    return {
        "search_endpoint": search_endpoint,
        "aoai_endpoint": aoai_endpoint,
        "embedding_deployment": embedding_deployment,
        "index_name": index_name,
    }


def load_seed(seed_path: Path) -> List[Dict[str, Any]]:
    """Load seed JSON."""
    with open(seed_path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def create_index(
    index_client: SearchIndexClient,
    index_name: str,
    aoai_endpoint: str,
    embedding_deployment: str,
) -> None:
    """Create or update servicios_index with vector and semantic search."""
    fields = [
        SearchField(name="id", type=SearchFieldDataType.String, key=True),
        SearchField(
            name="categoria",
            type=SearchFieldDataType.String,
            filterable=True,
            retrievable=True,
        ),
        SearchField(
            name="nombre",
            type=SearchFieldDataType.String,
            searchable=True,
            retrievable=True,
        ),
        SearchField(
            name="descripcion",
            type=SearchFieldDataType.String,
            searchable=True,
            retrievable=True,
        ),
        SearchField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            retrievable=True,
        ),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=1536,
            vector_search_profile_name="serviciosVectorProfile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="serviciosHnsw")],
        profiles=[
            VectorSearchProfile(
                name="serviciosVectorProfile",
                algorithm_configuration_name="serviciosHnsw",
                vectorizer_name="serviciosOpenAI",
            )
        ],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name="serviciosOpenAI",
                kind="azureOpenAI",
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=aoai_endpoint,
                    deployment_name=embedding_deployment,
                    model_name=embedding_deployment,
                ),
            )
        ],
    )

    semantic_config = SemanticConfiguration(
        name="servicios-semantic",
        prioritized_fields=SemanticPrioritizedFields(
            keywords_fields=[SemanticField(field_name="nombre")],
            content_fields=[SemanticField(field_name="content")],
        ),
    )
    semantic_search = SemanticSearch(configurations=[semantic_config])

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )
    index_client.create_or_update_index(index)
    print(f"Index '{index_name}' created/updated.")


def get_embeddings(
    client: AzureOpenAI,
    texts: List[str],
    deployment: str,
    batch_size: int = 10,
) -> List[List[float]]:
    """Get embeddings in batches."""
    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            resp = client.embeddings.create(input=batch, model=deployment)
            all_embeddings.extend([d.embedding for d in resp.data])
        except Exception as e:
            print(f"Batch failed: {e}, retrying individually...")
            for t in batch:
                try:
                    emb = client.embeddings.create(input=t, model=deployment)
                    all_embeddings.append(emb.data[0].embedding)
                except Exception:
                    all_embeddings.append([0.0] * 1536)
            time.sleep(1)
    return all_embeddings


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest OPTI services to Azure AI Search")
    parser.add_argument(
        "--seed",
        type=Path,
        default=_project_root / "data" / "servicios_opti_2026_seed.json",
        help="Path to seed JSON",
    )
    parser.add_argument("--skip-index", action="store_true", help="Skip index creation")
    args = parser.parse_args()

    if not args.seed.exists():
        raise SystemExit(f"Seed file not found: {args.seed}")

    cfg = get_config()
    docs = load_seed(args.seed)
    print(f"Loaded {len(docs)} documents from {args.seed}")

    credential = DefaultAzureCredential()
    index_client = SearchIndexClient(
        endpoint=cfg["search_endpoint"],
        credential=credential,
    )
    search_client = SearchClient(
        endpoint=cfg["search_endpoint"],
        index_name=cfg["index_name"],
        credential=credential,
    )

    if not args.skip_index:
        create_index(
            index_client,
            cfg["index_name"],
            cfg["aoai_endpoint"],
            cfg["embedding_deployment"],
        )
        time.sleep(2)

    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    openai_client = AzureOpenAI(
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=cfg["aoai_endpoint"],
        azure_ad_token_provider=token_provider,
    )

    contents = [content_for_embedding(d) for d in docs]
    print(f"Generating embeddings for {len(contents)} documents...")
    embeddings = get_embeddings(
        openai_client,
        contents,
        cfg["embedding_deployment"],
    )

    search_docs = []
    for i, (doc, content, emb) in enumerate(zip(docs, contents, embeddings)):
        search_docs.append({
            "id": doc["id"],
            "categoria": doc.get("categoria", ""),
            "nombre": doc.get("nombre", ""),
            "descripcion": doc.get("descripcion", ""),
            "content": content,
            "contentVector": emb,
        })
        if len(search_docs) >= 20:
            search_client.upload_documents(documents=search_docs)
            print(f"Uploaded {i + 1} documents...")
            search_docs = []

    if search_docs:
        search_client.upload_documents(documents=search_docs)
    print(f"Done. Uploaded {len(docs)} documents to {cfg['index_name']}.")


if __name__ == "__main__":
    main()
