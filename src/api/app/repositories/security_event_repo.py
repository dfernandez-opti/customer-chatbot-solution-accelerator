"""
Security event repository - JSONL para demo (sin Cosmos).
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# Persistencia: /home/LogFiles en App Service (requiere WEBSITES_ENABLE_APP_SERVICE_STORAGE=true)
# Si falla, fallback a /tmp (se pierde al reiniciar)
_EFFECTIVE_FILE: Optional[Path] = None
_FALLBACK_FILE = Path("/tmp/security-events.jsonl")


def _get_events_file() -> Path:
    global _EFFECTIVE_FILE
    if _EFFECTIVE_FILE is not None:
        return _EFFECTIVE_FILE
    _data_dir = os.environ.get("SECURITY_EVENTS_DATA_DIR")
    if _data_dir:
        base = Path(_data_dir).resolve()
    elif os.environ.get("WEBSITE_SITE_NAME"):
        base = Path("/home/LogFiles/data/security-events").resolve()
    else:
        base = Path("/tmp").resolve()
    _EFFECTIVE_FILE = base / "security-events.jsonl"
    return _EFFECTIVE_FILE


def _ensure_and_write(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return True
    except (OSError, PermissionError) as e:
        logger.warning("Cannot write to %s: %s", path, e)
        return False


def _load_events() -> List[dict]:
    events = []
    for path in [_get_events_file(), _FALLBACK_FILE]:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            break
        except Exception as e:
            logger.warning("Error loading security events from %s: %s", path, e)
    return events


def _append_event(event: dict):
    content = json.dumps(event, ensure_ascii=False) + "\n"
    primary = _get_events_file()
    if _ensure_and_write(primary, content):
        return
    if _ensure_and_write(_FALLBACK_FILE, content):
        logger.info(
            "Security events using fallback path %s (enable WEBSITES_ENABLE_APP_SERVICE_STORAGE for persistence)",
            _FALLBACK_FILE,
        )
        global _EFFECTIVE_FILE
        _EFFECTIVE_FILE = _FALLBACK_FILE
    else:
        logger.error("Failed to persist security event (no writable path)")


def create_security_event(
    session_id: str,
    attack_type: str,
    severity: str,
    prompt_hash: str,
    prompt_snippet: str,
    correlation_id: str,
    evidence: dict,
    user_id: Optional[str] = None,
    ip: Optional[str] = None,
    model_name: Optional[str] = None,
    route: str = "/api/chat/message",
    raw_prompt_stored: bool = False,
) -> dict:
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "session_id": session_id,
        "user_id": user_id,
        "ip": ip,
        "attack_type": attack_type,
        "severity": severity,
        "action": "blocked",
        "prompt_hash": prompt_hash,
        "prompt_snippet": prompt_snippet,
        "model_name": model_name,
        "route": route,
        "correlation_id": correlation_id,
        "evidence": evidence,
        "raw_prompt_stored": raw_prompt_stored,
        "export_status": "pending",
    }
    _append_event(event)
    return event


def list_security_events(limit: int = 50) -> List[dict]:
    events = _load_events()
    return list(reversed(events))[:limit]
