"""
Security events API - Secure GenAI Demo
"""

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/security", tags=["security"])

try:
    from ..repositories.security_event_repo import list_security_events
except ImportError:
    from app.repositories.security_event_repo import list_security_events


@router.get("/events")
async def get_security_events(limit: int = Query(50, ge=1, le=100)):
    """Lista últimos eventos de seguridad."""
    events = list_security_events(limit=limit)
    return events


@router.post("/export")
async def export_security_event():
    """Stub: exporta evento a EXPORT_URL si está configurado."""
    return {"status": "stub", "message": "Export hook not implemented"}
