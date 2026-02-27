"""
Opportunity repository - JSONL para demo (sin Cosmos).
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# Persistencia: en App Service /tmp se pierde al reiniciar. Usar /home/LogFiles si existe.
_DATA_DIR = os.environ.get("OPPORTUNITIES_DATA_DIR")
if _DATA_DIR:
    DATA_DIR = Path(_DATA_DIR).resolve()
elif os.environ.get("WEBSITE_SITE_NAME"):  # App Service
    DATA_DIR = Path("/home/LogFiles/data/opportunities").resolve()
else:
    DATA_DIR = Path("/tmp").resolve()
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.jsonl"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_opportunities() -> List[dict]:
    _ensure_data_dir()
    if not OPPORTUNITIES_FILE.exists():
        return []
    items = []
    try:
        with open(OPPORTUNITIES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.warning("Error loading opportunities: %s", e)
    return items


def _append_opportunity(opp: dict):
    _ensure_data_dir()
    try:
        with open(OPPORTUNITIES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(opp, ensure_ascii=False) + "\n")
        logger.info("Oportunidad guardada en %s", OPPORTUNITIES_FILE)
    except Exception as e:
        logger.error("Error appending opportunity to %s: %s", OPPORTUNITIES_FILE, e, exc_info=True)


def create_opportunity(
    phone: str,
    company: str,
    service: str,
    contact_name: Optional[str] = None,
    email: Optional[str] = None,
    session_id: Optional[str] = None,
    user_message_snippet: Optional[str] = None,
) -> dict:
    """Crea una oportunidad de cotización. Se guarda en JSONL (por defecto /tmp/opportunities.jsonl)."""
    opp = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "phone": phone,
        "company": company,
        "service": service,
        "contact_name": contact_name,
        "email": email,
        "status": "new",
        "session_id": session_id,
        "user_message_snippet": user_message_snippet,
        "intent_confidence": 1.0,
    }
    _append_opportunity(opp)
    return opp


def list_opportunities(limit: int = 50) -> List[dict]:
    """Lista oportunidades (más recientes primero)."""
    items = _load_opportunities()
    return list(reversed(items))[:limit]


def count_opportunities() -> int:
    """Cuenta total de oportunidades."""
    return len(_load_opportunities())
