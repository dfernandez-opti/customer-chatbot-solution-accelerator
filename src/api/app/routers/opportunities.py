# Opportunities API - cotizaciones y oportunidades de negocio
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..repositories.opportunity_repo import (
    create_opportunity,
    list_opportunities,
    count_opportunities,
)

router = APIRouter(prefix="/api", tags=["opportunities"])


class OpportunityCreate(BaseModel):
    """Payload para crear una oportunidad."""

    phone: str = Field(..., min_length=1, description="Teléfono del cliente")
    company: str = Field(..., min_length=1, description="Nombre de la empresa")
    service: str = Field(..., min_length=1, description="Servicio de interés (ej: IA, BRE, SEC)")
    contact_name: Optional[str] = None
    email: Optional[str] = None
    session_id: Optional[str] = None
    user_message_snippet: Optional[str] = None


@router.get("/opportunities")
async def get_opportunities():
    """Lista oportunidades detectadas (purchase intent / cotizaciones)."""
    return list_opportunities(limit=50)


@router.get("/opportunities/summary")
async def get_opportunities_summary():
    """Resumen para el dashboard: total de oportunidades."""
    return {"total": count_opportunities()}


@router.post("/opportunities")
async def post_opportunity(payload: OpportunityCreate):
    """Registra una nueva oportunidad. Se guarda en el sistema (JSONL por defecto en /tmp/opportunities.jsonl)."""
    opp = create_opportunity(
        phone=payload.phone,
        company=payload.company,
        service=payload.service,
        contact_name=payload.contact_name,
        email=payload.email,
        session_id=payload.session_id,
        user_message_snippet=payload.user_message_snippet,
    )
    return {
        "id": opp["id"],
        "message": "Oportunidad registrada correctamente",
        "timestamp": opp["timestamp"],
    }
