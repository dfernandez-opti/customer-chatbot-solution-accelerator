#!/usr/bin/env python3
"""
Ingest OPTI services seed JSON to Cosmos DB.
Uses env vars: COSMOS_ENDPOINT, COSMOS_DATABASE, COSMOS_CONTAINER (optional).
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Tuple

from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Add project root for catalog imports
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "src"))

# Cargar .env: raiz del proyecto o src/api (donde la API tambien lee)
load_dotenv(_project_root / ".env")
load_dotenv(_project_root / "src" / "api" / ".env")

from catalog.schema import validate_servicio


def get_config() -> Tuple[str, str, str]:
    """Read config from environment."""
    endpoint = (
        os.getenv("COSMOS_ENDPOINT")
        or os.getenv("COSMOS_DB_ENDPOINT")
        or os.getenv("AZURE_COSMOSDB_ENDPOINT")
        or os.getenv("COSMOSDB_ENDPOINT")
    )
    if not endpoint:
        account = os.getenv("AZURE_COSMOSDB_ACCOUNT")
        if account:
            endpoint = f"https://{account}.documents.azure.com:443/"
    if not endpoint:
        raise SystemExit(
            "Missing Cosmos endpoint. Set COSMOS_DB_ENDPOINT or COSMOS_ENDPOINT in .env "
            "(copy .env.example to .env and fill values)."
        )
    if not endpoint.startswith("https://"):
        endpoint = f"https://{endpoint}.documents.azure.com:443/"
    database = (
        os.getenv("COSMOS_DATABASE")
        or os.getenv("COSMOS_DB_DATABASE_NAME")
        or os.getenv("AZURE_COSMOSDB_DATABASE")
        or "ecommerce_db"
    )
    container_name = os.getenv("COSMOS_SERVICIOS_CONTAINER", "servicios")
    return endpoint, database, container_name


def load_seed(seed_path: Path) -> List[Dict[str, Any]]:
    """Load and validate seed JSON."""
    with open(seed_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("Seed JSON must be an array of service documents.")
    for i, doc in enumerate(data):
        err = validate_servicio(doc)
        if err:
            raise SystemExit(f"Invalid document at index {i}: {err}")
    return data


def prepare_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Add timestamps and ensure source structure."""
    now = datetime.utcnow().isoformat() + "Z"
    out = dict(doc)
    if not out.get("createdAt"):
        out["createdAt"] = now
    out["updatedAt"] = now
    if "source" in out and isinstance(out["source"], dict):
        if "document" not in out["source"]:
            out["source"]["document"] = "Servicios Opti (1) (1).pdf"
        if "pages" not in out["source"]:
            out["source"]["pages"] = []
    else:
        out["source"] = {"document": "Servicios Opti (1) (1).pdf", "pages": []}
    return out


def upsert_with_retry(container, item: Dict[str, Any], max_retries: int = 6) -> bool:
    """Upsert item with retry on transient errors. Returns True if new, False if updated."""
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            container.upsert_item(item)
            return True
        except exceptions.CosmosHttpResponseError as e:
            status = getattr(e, "status_code", None)
            if status in (429, 408, 500, 502, 503, 504):
                sleep(backoff)
                backoff = min(backoff * 2, 16)
                continue
            if status in (401, 403):
                raise SystemExit(
                    "Unauthorized. Ensure your identity has "
                    "'Cosmos DB Built-in Data Contributor' role."
                ) from e
            raise
    raise RuntimeError(f"Failed to upsert after {max_retries} retries")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest OPTI services seed to Cosmos DB")
    parser.add_argument(
        "--seed",
        type=Path,
        default=_project_root / "data" / "servicios_opti_2026_seed.json",
        help="Path to seed JSON file",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not write")
    args = parser.parse_args()

    if not args.seed.exists():
        raise SystemExit(f"Seed file not found: {args.seed}")

    docs = load_seed(args.seed)
    print(f"Loaded {len(docs)} service documents from {args.seed}")

    if args.dry_run:
        print("Dry run: validation passed, no writes.")
        return

    endpoint, database_name, container_name = get_config()
    credential = DefaultAzureCredential()
    client = CosmosClient(endpoint, credential=credential)

    database = client.create_database_if_not_exists(id=database_name)
    container = database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path="/categoria"),
    )
    print(f"Container '{container_name}' ready (partition: /categoria)")

    inserted = 0
    updated = 0
    errors: List[str] = []

    for doc in docs:
        try:
            prepared = prepare_doc(doc)
            upsert_with_retry(container, prepared)
            inserted += 1
        except Exception as e:
            errors.append(f"{doc.get('id', '?')}: {e}")

    print(f"\nSummary:")
    print(f"  Inserted/Updated: {inserted}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for err in errors[:10]:
            print(f"    - {err}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
    else:
        print(f"  Errors: 0")
    print("Done.")


if __name__ == "__main__":
    main()
