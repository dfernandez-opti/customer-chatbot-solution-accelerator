"""Schema and validation for OPTI services catalog documents."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    """Source document metadata."""

    document: str = Field(default="Servicios Opti (1) (1).pdf")
    pages: List[int] = Field(default_factory=list)


class ServicioDocument(BaseModel):
    """RAG-ready document for a single OPTI service."""

    id: str = Field(..., description="Stable deterministic ID (categoria*slug*version)")
    categoria: str = Field(
        ...,
        description="Category: Seguridad | ITSM | Cloud & Data | Desarrollo | Servicios Administrados | IA | CSP",
    )
    nombre: str = Field(..., description="Service display name")
    descripcion: str = Field(default="", description="Brief description")
    problemas_que_resuelve: List[str] = Field(default_factory=list)
    incluye: List[str] = Field(default_factory=list)
    beneficios: List[str] = Field(default_factory=list)
    tecnologias: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    faq_examples: List[str] = Field(default_factory=list)
    source: SourceInfo = Field(default_factory=SourceInfo)
    createdAt: str = Field(default="")
    updatedAt: str = Field(default="")
    version: str = Field(default="2026.1")

    def to_cosmos_dict(self) -> Dict[str, Any]:
        """Convert to dict suitable for Cosmos DB upsert."""
        now = datetime.utcnow().isoformat() + "Z"
        d = self.model_dump()
        if not d.get("createdAt"):
            d["createdAt"] = now
        d["updatedAt"] = now
        d["source"] = self.source.model_dump()
        return d


def validate_servicio(doc: Dict[str, Any]) -> Optional[str]:
    """Validate a document and return error message or None."""
    try:
        ServicioDocument(**doc)
        return None
    except Exception as e:
        return str(e)
