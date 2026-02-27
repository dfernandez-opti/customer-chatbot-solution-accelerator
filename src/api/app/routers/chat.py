import asyncio
import logging
import random
import re
from datetime import datetime
from typing import Any, Dict, Optional

import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

# Handle both local debugging and Docker deployment with conditional imports
try:
    # Try relative imports first (for Docker)
    from ..auth import get_current_user_optional
    from ..config import settings, has_content_safety_config
    from ..services.chat_service import get_chat_service
    from ..models import (
        APIResponse,
        ChatMessageCreate,
        ChatMessageType,
        ChatSessionCreate,
        ChatSessionUpdate,
    )
except ImportError:
    # Fall back to absolute imports (for local debugging)
    import os
    import sys

    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    from app.models import (
        ChatMessageCreate,
        ChatSessionCreate,
        ChatSessionUpdate,
        APIResponse,
        ChatMessageType,
    )
    from app.services.chat_service import get_chat_service

    from app.config import settings, has_content_safety_config
    from app.auth import get_current_user_optional

from agent_framework.azure import AzureAIProjectAgentProvider
from azure.ai.projects.aio import AIProjectClient

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def format_timestamp(dt: datetime) -> str:
    """Helper function to format timestamps consistently"""
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


# Regex para extraer datos de contacto del mensaje del usuario
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_SERVICES = [
    "Boutique de Recursos Especializados", "Servicios de Inteligencia Artificial",
    "IA", "BRE", "SEC", "ITSM", "CSP", "Cloud and Data", "Servicios Administrados", "ADM", "SEG",
    "Inteligencia Artificial", "Ciberseguridad",
]
_CONFIRM_WORDS = re.compile(r"^(si|sí|sip|ok|okey|correcto|dale|vale|perfecto|de acuerdo|claro|afirmativo|yes)$", re.I)

_GREETING_PATTERNS = re.compile(
    r"^(hola|holi|holis|buenos?\s*d[ií]as|buenas?\s*tardes|buenas?\s*noches|"
    r"hey|hi|hello|saludos|qu[eé]\s*tal|qu[eé]\s*hay|buenas?|"
    r"buen\s*d[ií]a|buen\s*d[ií]as)$",
    re.I,
)


def _is_greeting(text: str) -> bool:
    """Detecta saludos simples para responder sin llamar al agente."""
    if not text or len(text.strip()) > 50:
        return False
    return bool(_GREETING_PATTERNS.match(text.strip()))


_GREETING_RESPONSES = [
    "¡Hola! Soy el asistente de OPTI. ¿En qué te puedo ayudar hoy? Tengo información sobre nuestros servicios de ciberseguridad, IA, CSP, Cloud y más.",
    "¡Buen día! Estoy aquí para ayudarte con lo que necesites de OPTI — servicios, cotizaciones, políticas. ¿Qué te interesa?",
    "Hola, ¿cómo estás? Soy el asistente de OPTI. Puedo orientarte sobre nuestro portafolio o ayudarte a iniciar una cotización. ¿Por dónde empezamos?",
    "¡Hey! Soy el asistente de OPTI. Dime, ¿qué necesitas? Puedo hablar de ciberseguridad, inteligencia artificial, soluciones cloud, o lo que necesites.",
    "Hola. ¿En qué te puedo ayudar? Si buscas información sobre algún servicio o quieres cotizar, con gusto te oriento.",
]


def _get_greeting_response() -> str:
    """Respuesta amigable para saludos (variada para tono más natural)."""
    return random.choice(_GREETING_RESPONSES)


def _strip_leaked_instructions(text: str) -> str:
    """Elimina filtración de prompt/instrucciones del agente en la respuesta."""
    if not text or not isinstance(text, str):
        return text or ""
    result = text
    # Si el modelo incluyó sus instrucciones, truncar desde el inicio de la filtración
    leak_markers = [
        "Eres un asesor comercial",
        "Eres un asistente",
        "Tu objetivo es generar leads",
        "## TU PERSONALIDAD",
        "## HERRAMIENTAS",
        "## CATÁLOGO DE SERVICIOS",
        "## FLUJO PARA REGISTRAR",
        "## REGLA CRÍTICA",
        "## REGLAS GENERALES",
        "## RAI - Seguridad",
    ]
    result_lower = result.lower()
    for marker in leak_markers:
        idx = result_lower.find(marker.lower())
        if idx != -1:
            result = result[:idx].strip()
            break
    return result


def _remove_contact_prompt_for_informational(text: str) -> str:
    """Quita la solicitud de contacto cuando es pregunta informativa."""
    if not text or not isinstance(text, str):
        return text or ""
    result = text
    # Patrones exactos
    contact_patterns = [
        "\n\n¿Te gustaría que te contactemos para más detalles o una cotización? Comparte tu nombre, correo, teléfono y empresa.",
        "\n\n¿Te gustaría que te contactemos para la cotización? Comparte tu nombre, correo, teléfono y empresa.",
        "\n\n¿Te gustaría que te contactemos? Comparte tu nombre, correo, teléfono y empresa.",
        "\n\nComparte tu nombre, correo, teléfono y empresa.",
        "¿Te gustaría que te contactemos para más detalles o una cotización? Comparte tu nombre, correo, teléfono y empresa.",
        "¿Te gustaría que te contactemos para la cotización? Comparte tu nombre, correo, teléfono y empresa.",
        "¿Te gustaría que te contactemos? Comparte tu nombre, correo, teléfono y empresa.",
        "Comparte tu nombre, correo, teléfono y empresa.",
    ]
    for pat in contact_patterns:
        result = result.replace(pat, "").strip()
    # Regex: cualquier variación de "¿Te gustaría...? Comparte tu nombre, correo, teléfono y empresa"
    result = re.sub(
        r"\s*¿Te gustaría[^?]*\?\s*Comparte tu nombre, correo, teléfono y empresa\.?\s*",
        "",
        result,
        flags=re.IGNORECASE,
    ).strip()
    # Catch-all: desde "¿Te gustaría" hasta "empresa." (cualquier texto intermedio)
    result = re.sub(
        r"\s*¿Te gustaría[^.]*?Comparte tu nombre, correo, teléfono y empresa\.?\s*",
        "",
        result,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    # Solo "Comparte tu nombre..." al final
    result = re.sub(
        r"\s*Comparte tu nombre, correo, teléfono y empresa\.?\s*$",
        "",
        result,
        flags=re.IGNORECASE,
    ).strip()
    # Fallback nuclear: si aún queda "¿Te gustaría...Comparte tu nombre", truncar desde ahí
    idx = result.lower().find("¿te gustaría")
    if idx != -1 and "comparte tu nombre" in result[idx:].lower():
        result = result[:idx].strip()
    return result


def _extract_phone(text: str) -> Optional[str]:
    """Extrae teléfono: secuencia de 10-15 dígitos (permite espacios/guiones)."""
    digits = re.sub(r"\D", "", text)
    for i in range(len(digits) - 9):
        chunk = digits[i : i + 15]
        if 10 <= len(chunk) <= 15:
            return chunk
    return None


def _extract_contact_from_context(context_str: str) -> Optional[dict]:
    """
    Extrae datos de contacto del mensaje del Asistente que liste "Datos proporcionados".
    Formato: 1) Nombre completo: X 2) Correo electrónico: Y 3) Teléfono: Z 4) Empresa: W 5) Servicio: S
    """
    if not context_str or ("Datos proporcionados" not in context_str and "datos que tengo" not in context_str.lower()):
        return None
    name = email = phone = company = service = None
    # Nombre: hasta 2) o newline
    m = re.search(r"Nombre completo[:\s]+([^\n]+?)(?=\s*\d\)|\n|$)", context_str, re.I)
    if m:
        name = m.group(1).strip().rstrip(",")
    # Email
    m = re.search(r"Correo electr[oó]nico[:\s]+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", context_str, re.I)
    if m:
        email = m.group(1).strip()
    # Teléfono: dígitos
    m = re.search(r"Tel[eé]fono[:\s]+([0-9\s\-]{10,20})", context_str, re.I)
    if m:
        phone = re.sub(r"\D", "", m.group(1))
        if len(phone) < 10:
            phone = None
    # Empresa
    m = re.search(r"Nombre de empresa[:\s]+([^\n]+?)(?=\s*\d\)|\n|$)", context_str, re.I)
    if m:
        company = m.group(1).strip().rstrip(",")
    # Servicio
    m = re.search(r"Servicio de inter[eé]s[:\s]+([^\n?]+?)(?=\s*\d\)|\n|\?|$)", context_str, re.I)
    if m:
        service = m.group(1).strip().rstrip(",")
    if phone and company and service:
        return {"name": name, "email": email, "phone": phone, "company": company, "service": service}
    return None


def _try_register_opportunity_from_message(
    user_content: str,
    context_str: str,
    session_id: str,
) -> tuple[bool, bool]:
    """
    Fallback: extrae datos de contacto y registra oportunidad.
    Returns (registered, from_confirmation).
    """
    if not user_content:
        return False, False
    try:
        from ..repositories.opportunity_repo import create_opportunity

        text = user_content.strip()

        # Caso 1: Usuario confirma "sí", "ok" y el contexto tiene datos listados por el Asistente
        if _CONFIRM_WORDS.match(text) and context_str:
            extracted = _extract_contact_from_context(context_str)
            if extracted:
                create_opportunity(
                    phone=extracted["phone"],
                    company=extracted["company"],
                    service=extracted["service"],
                    contact_name=extracted.get("name"),
                    email=extracted.get("email"),
                    session_id=session_id,
                    user_message_snippet=f"Confirmación: {text[:50]}",
                )
                logger.info("Oportunidad registrada desde confirmación: %s", {"company": extracted["company"]})
                return True, True

        # Caso 2: Mensaje con datos de contacto explícitos
        if len(text) < 8:
            return False, False
        email_match = _EMAIL_RE.search(text)
        email = email_match.group(0) if email_match else None
        phone = _extract_phone(text)
        if not phone:
            return False, False

        parts = [p.strip() for p in re.split(r"\s*,\s*", text) if p.strip()]
        name = None
        company = None
        for p in parts:
            if "@" in p and "." in p:
                continue
            if p.replace(" ", "").replace("-", "").isdigit() and len(p.replace(" ", "")) >= 10:
                continue
            if not name and len(p) > 2 and not p.isdigit():
                name = p
            elif len(p) > 1 and p != name and not p.isdigit():
                company = p

        if not company:
            company = "Cliente"

        service = "Cotización"
        if context_str:
            for svc in _SERVICES:
                if svc.lower() in context_str.lower():
                    service = svc
                    break

        create_opportunity(
            phone=phone,
            company=company,
            service=service,
            contact_name=name,
            email=email,
            session_id=session_id,
            user_message_snippet=text[:200],
        )
        logger.info("Oportunidad registrada desde fallback: %s", {"phone": phone[:4] + "***", "company": company})
        return True, False
    except Exception as e:
        logger.exception("Fallback register_opportunity falló: %s", e)
        return False, False


# Mapeo pregunta -> producto para fallback cuando AI Search no devuelve datos
_PRODUCT_KEYWORDS = [
    ("cloud solution provider", "OPT-CSP"),
    ("csp", "OPT-CSP"),
    ("inteligencia artificial", "OPT-IA"),
    ("servicios de inteligencia artificial", "OPT-IA"),
    ("servicios de ia", "OPT-IA"),
    ("ia ", "OPT-IA"),
    ("boutique", "OPT-BRE"),
    ("recursos especializados", "OPT-BRE"),
    ("bre", "OPT-BRE"),
    ("sec", "OPT-SEC"),
    ("ciberseguridad", "OPT-SEC"),
    ("itsm", "OPT-ITSM"),
    ("servicios administrados", "OPT-ADM"),
    ("adm", "OPT-ADM"),
    ("cloud and data", "OPT-CD"),
    ("cloud y datos", "OPT-CD"),
    ("seguridad integral", "OPT-SEG"),
    ("seg ", "OPT-SEG"),
]


def _get_product_fallback_response(user_question: str) -> Optional[str]:
    """
    Cuando el agente no encuentra info en AI Search, busca en el catálogo local (DEMO_PRODUCTS).
    Devuelve texto con la descripción del servicio si hay match.
    Solo incluye oferta de contacto si el usuario explícitamente pide cotización.
    """
    if not user_question or len(user_question.strip()) < 2:
        return None
    q = user_question.lower().strip()
    matched_id = None
    for keyword, product_id in _PRODUCT_KEYWORDS:
        if keyword in q:
            matched_id = product_id
            break
    if not matched_id:
        return None
    # Solo pedir datos si el usuario explícitamente pide cotización o contacto
    wants_quote = any(
        kw in q for kw in [
            "cotización", "cotizar", "cotiza", "contacten", "contacto",
            "contáctenme", "me interesa", "quiero que me", "presupuesto",
        ]
    )
    try:
        from ..services.demo_products import DEMO_PRODUCTS
        for p in DEMO_PRODUCTS:
            if p.id == matched_id:
                base = f"**{p.title}** ({p.category})\n\n{p.description}"
                if wants_quote:
                    base += (
                        "\n\n¿Te gustaría que te contactemos para la cotización? "
                        "Comparte tu nombre, correo, teléfono y empresa."
                    )
                else:
                    base += "\n\n¿Qué área te interesa o qué necesitas para tu empresa?"
                return base
    except Exception as e:
        logger.debug("Product fallback error: %s", e)
    return None


def _blocked_reason_to_user_message(reason: str) -> str:
    """Mensaje claro para que el usuario entienda qué hizo mal."""
    messages = {
        "violence": "Tu mensaje fue bloqueado porque contiene referencias a violencia. Por favor reformula tu consulta. Puedo ayudarte con servicios de OPTI, cotizaciones o políticas.",
        "self_harm": "Por tu seguridad, no puedo procesar solicitudes relacionadas con autolesión. Si necesitas apoyo, contacta a profesionales de salud. ¿En qué más puedo ayudarte sobre nuestros servicios?",
        "hate": "Tu mensaje fue bloqueado por contener contenido discriminatorio. Puedo ayudarte con información sobre servicios de OPTI, cotizaciones o políticas.",
        "sexual": "Tu mensaje fue bloqueado por contener contenido inapropiado. ¿Puedo ayudarte con nuestros servicios, cotizaciones o información de OPTI?",
        "prompt_injection": "Tu solicitud fue bloqueada porque intenta modificar el comportamiento del asistente. Puedo ayudarte con servicios de OPTI, cotizaciones o políticas. Prueba con: «¿Qué servicios de ciberseguridad ofrece OPTI?»",
        "jailbreak": "Tu solicitud fue bloqueada por intentar eludir las restricciones del asistente. ¿En qué puedo ayudarte sobre nuestros servicios o cotizaciones?",
        "data_exfiltration": "No puedo compartir código fuente, credenciales ni información sensible. ¿Puedo ayudarte con información sobre servicios de OPTI o cotizaciones?",
        "credential_theft": "No puedo ayudar con solicitudes relacionadas con contraseñas o credenciales. ¿Necesitas información sobre nuestros servicios o políticas?",
    }
    return messages.get(reason, "Tu mensaje fue bloqueado por políticas de seguridad. ¿Puedo ayudarte con servicios de OPTI, cotizaciones o políticas?")


@router.get("/debug-product-fallback")
async def debug_product_fallback(q: str = ""):
    """Debug: verifica si una pregunta activaría el fallback de productos."""
    if not q:
        return {"message": "Pasa ?q=tu+pregunta para probar"}
    fallback = _get_product_fallback_response(q)
    return {
        "query": q,
        "has_fallback": fallback is not None,
        "preview": fallback[:200] + "..." if fallback and len(fallback) > 200 else fallback,
    }


@router.get("/debug-search-index")
async def debug_search_index():
    """Debug: verifica documentos en products_index (usado por el agente). No requiere az."""
    try:
        from ..utils.azure_credential_utils import get_azure_credential
        from azure.search.documents import SearchClient

        import os
        endpoint = settings.azure_search_endpoint or os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        if not endpoint:
            return {"error": "AZURE_SEARCH_ENDPOINT o AZURE_AI_SEARCH_ENDPOINT no configurado"}

        credential = get_azure_credential(client_id=str(settings.azure_client_id) if settings.azure_client_id else None)
        client = SearchClient(
            endpoint=endpoint,
            index_name="products_index",
            credential=credential,
        )
        results = client.search(search_text="*", include_total_count=True, top=0)
        count = results.get_count()
        return {
            "index": "products_index",
            "document_count": count,
            "status": "ok" if count and count > 0 else "vacío",
        }
    except Exception as e:
        logger.exception("debug-search-index error: %s", e)
        return {"error": str(e), "index": "products_index"}


@router.get("/sessions")
async def get_chat_sessions(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Get all chat sessions for a user"""
    try:
        user_id = current_user.get("user_id") if current_user else None
        if not user_id:
            # Return empty list for anonymous users
            return []

        sessions = await get_chat_service().get_chat_sessions_by_user(user_id)
        return [
            {
                "id": session.id,
                "session_name": session.session_name,
                "message_count": session.message_count,
                "last_message_at": session.last_message_at,
                "is_active": session.is_active,
                "created_at": session.created_at,
            }
            for session in sessions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching chat sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """Get a specific chat session with messages"""
    try:
        user_id = current_user.get("user_id") if current_user else None
        session = await get_chat_service().get_chat_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        return {
            "id": session.id,
            "session_name": session.session_name,
            "message_count": session.message_count,
            "last_message_at": session.last_message_at,
            "is_active": session.is_active,
            "created_at": session.created_at,
            "messages": [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "sender": msg.message_type,
                    "timestamp": format_timestamp(msg.created_at),
                    "metadata": msg.metadata,
                }
                for msg in session.messages
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching chat session: {str(e)}"
        )


@router.post("/sessions", response_model=APIResponse)
async def create_chat_session(session: ChatSessionCreate):
    """Create a new chat session"""
    try:
        new_session = await get_chat_service().create_chat_session(session)
        return APIResponse(
            message="Chat session created successfully",
            data={
                "id": new_session.id,
                "session_name": new_session.session_name,
                "user_id": new_session.user_id,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating chat session: {str(e)}"
        )


@router.put("/sessions/{session_id}")
async def update_chat_session(
    session_id: str, session_update: ChatSessionUpdate, user_id: Optional[str] = None
):
    """Update a chat session"""
    try:
        updated_session = await get_chat_service().update_chat_session(
            session_id, session_update, user_id
        )
        if not updated_session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        return {
            "id": updated_session.id,
            "session_name": updated_session.session_name,
            "is_active": updated_session.is_active,
            "message_count": updated_session.message_count,
            "updated_at": updated_session.updated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating chat session: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str, user_id: Optional[str] = None):
    """Delete a chat session"""
    try:
        success = await get_chat_service().delete_chat_session(session_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Chat session not found")

        return APIResponse(message="Chat session deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting chat session: {str(e)}"
        )


# @router.post("/sessions/{session_id}/messages")
# async def send_message(
#     session_id: str,
#     message: ChatMessageCreate,
#     current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
# ):
#     """Send a message to a chat session"""
#     try:
#         user_id = current_user.get("user_id") if current_user else None

#         # Add user message to session
#         session = await get_chat_service().add_message_to_session(
#             session_id, message, user_id
#         )

#         # Generate AI response with thread caching and user context
#         ai_content = await generate_ai_response(
#             message.content, session.messages, session_id=session_id, user_id=user_id
#         )

#         # Create AI response message
#         ai_response = ChatMessageCreate(
#             content=ai_content,
#             message_type=ChatMessageType.ASSISTANT,
#             metadata={
#                 "type": "ai_response",
#                 "original_message_id": session.messages[-1].id,
#             },
#         )

#         # Add AI response to session
#         updated_session = await get_chat_service().add_message_to_session(
#             session_id, ai_response, user_id
#         )

#         # Return the latest message (AI response)
#         latest_message = updated_session.messages[-1]
#         return {
#             "id": latest_message.id,
#             "content": latest_message.content,
#             "sender": latest_message.message_type,
#             "timestamp": format_timestamp(latest_message.created_at),
#             "metadata": latest_message.metadata,
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


# Legacy endpoints for backward compatibility
@router.get("/history")
async def get_chat_history(
    session_id: str = "default",
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """Get chat history for a session (legacy endpoint)"""
    try:
        user_id = current_user.get("user_id") if current_user else None
        # Use consistent session ID logic
        if session_id == "default":
            if user_id:
                session_id = f"user_{user_id}_default"
            else:
                session_id = "anonymous_default"

        session = await get_chat_service().get_chat_session(session_id, user_id)
        if not session:
            return []

        return [
            {
                "id": msg.id,
                "content": msg.content,
                "sender": msg.message_type,
                "timestamp": format_timestamp(msg.created_at),
            }
            for msg in session.messages
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching chat history: {str(e)}"
        )


@router.post("/message")
async def send_message_legacy(
    request: Request,
    message: ChatMessageCreate,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    try:
        user_id = current_user.get("user_id") if current_user else None
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        client_ip = request.client.host if request.client else None

        if hasattr(message, "session_id") and message.session_id:
            session_id = message.session_id
        elif user_id:
            session_id = f"user_{user_id}_default"
        else:
            session_id = "anonymous_default"

        # Safety: pattern detector + Content Safety (si configurado)
        if message.content:
            from ..services.safety import evaluate_safety

            safety_result = await evaluate_safety(
                prompt=message.content,
                metadata={"session_id": session_id, "user_id": user_id},
                content_safety_endpoint=settings.content_safety_endpoint if has_content_safety_config() else None,
                content_safety_key=settings.content_safety_key if has_content_safety_config() else None,
            )
            if not safety_result.allowed:
                prompt_hash = hashlib.sha256(message.content.encode()).hexdigest()
                snippet = (message.content[:200] + "...") if len(message.content) > 200 else message.content
                from ..repositories.security_event_repo import create_security_event

                create_security_event(
                    session_id=session_id,
                    attack_type=safety_result.blocked_reason.value if safety_result.blocked_reason else "other",
                    severity=safety_result.severity.value,
                    prompt_hash=prompt_hash,
                    prompt_snippet=snippet,
                    correlation_id=correlation_id,
                    evidence=safety_result.evidence,
                    user_id=user_id,
                    ip=client_ip,
                )
                logger.warning(
                    "SECURITY_EVENT | blocked | session=%s | type=%s | correlation=%s",
                    session_id,
                    safety_result.blocked_reason,
                    correlation_id,
                )
                # Evento estructurado para alertas en Azure Monitor / Sentinel / Defender
                try:
                    from opentelemetry import trace
                    span = trace.get_current_span()
                    if span.is_recording():
                        span.add_event(
                            "ContentSafetyBlocked",
                            attributes={
                                "security.event": "blocked",
                                "attack_type": safety_result.blocked_reason.value if safety_result.blocked_reason else "other",
                                "session_id": str(session_id),
                                "correlation_id": str(correlation_id),
                                "severity": safety_result.severity.value,
                            },
                        )
                except Exception:
                    pass
                # Mensaje personalizado para que el usuario entienda qué hizo mal
                reason = safety_result.blocked_reason.value if safety_result.blocked_reason else "other"
                user_message = _blocked_reason_to_user_message(reason)
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": user_message,
                        "blocked": True,
                        "blocked_reason": safety_result.blocked_reason.value if safety_result.blocked_reason else "other",
                        "attack_type": safety_result.blocked_reason.value if safety_result.blocked_reason else "other",
                        "severity": safety_result.severity.value,
                        "evidence": safety_result.evidence,
                        "correlation_id": correlation_id,
                        "suggested_prompts": [
                            "¿Qué servicios de ciberseguridad ofrece OPTI?",
                            "¿Cómo puedo solicitar una cotización para Servicios Administrados?",
                        ],
                    },
                )

        # Add user message to session
        await get_chat_service().add_message_to_session(session_id, message, user_id)

        # Saludos: responder directo sin llamar al agente
        if _is_greeting(message.content or ""):
            greeting = _get_greeting_response()
            ai_response = ChatMessageCreate(
                content=greeting,
                message_type=ChatMessageType.ASSISTANT,
                metadata={"type": "greeting"},
            )
            await get_chat_service().add_message_to_session(
                session_id, ai_response, user_id
            )
            return {
                "id": session_id,
                "content": greeting,
                "sender": "assistant",
                "timestamp": format_timestamp(datetime.utcnow()),
            }

        # NO usar product_fallback aquí: dejar que el agente (DSPM-AI-Project) responda.
        # El product_fallback solo se usa al final si el agente dice "no encontré" (líneas ~831).

        # Build context from conversation history (last 10 messages) so "sí", "ok" have meaning
        session_with_history = await get_chat_service().get_chat_session(session_id, user_id)
        context_parts = []
        if session_with_history and session_with_history.messages:
            # Use last 10 messages to avoid token overflow
            recent = session_with_history.messages[-10:]
            for msg in recent:
                role = "Usuario" if msg.message_type == ChatMessageType.USER else "Asistente"
                content = (msg.content or "").strip()
                if content:
                    context_parts.append(f"{role}: {content}")
        if context_parts:
            context_str = "\n".join(context_parts)
            question = (
                f"Esta es una conversación en curso con un cliente de OPTI:\n\n"
                f"{context_str}\n\n"
                f"Continúa la conversación de forma natural. "
                f"Usa el contexto previo para no repetir información ya dada. "
                f"Responde directamente al último mensaje del Usuario. "
                f"Varía el tono y la estructura según lo que el cliente necesite."
            )
        else:
            context_str = ""
            question = message.content

        # Fallback: registrar oportunidad si hay datos en mensaje o si usuario confirma "sí" con datos en contexto
        # (la herramienta register_opportunity del agente puede fallar en Foundry cloud)
        _, registered_from_confirmation = _try_register_opportunity_from_message(
            user_content=message.content or "",
            context_str=context_str,
            session_id=session_id,
        )

        ai_project_endpoint = settings.azure_foundry_endpoint
        chat_agent_name = settings.foundry_chat_agent
        product_agent_name = settings.foundry_product_agent
        policy_agent_name = settings.foundry_policy_agent

        # Demo fallback when Foundry is not configured (local dev)
        if not ai_project_endpoint or not chat_agent_name:
            product_fallback = _get_product_fallback_response(message.content or "")
            demo_response = (
                product_fallback
                if product_fallback
                else (
                    "OPTI ofrece servicios de ciberseguridad, gobernanza y transformación digital. "
                    "¿En qué puedo ayudarte? Puedes preguntar por servicios, cotizaciones o políticas."
                )
            )
            ai_response = ChatMessageCreate(
                content=demo_response,
                message_type=ChatMessageType.ASSISTANT,
                metadata={"type": "demo_fallback"},
            )
            await get_chat_service().add_message_to_session(
                session_id, ai_response, user_id
            )
            return {
                "id": session_id,
                "content": demo_response,
                "sender": "assistant",
                "timestamp": format_timestamp(datetime.utcnow()),
            }

        # Validate Azure AI Foundry configuration before creating the client/provider
        if not ai_project_endpoint:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Azure AI Foundry is not configured: 'azure_foundry_endpoint' is missing or empty. "
                    "Please configure this setting to enable chat functionality."
                ),
            )
        missing_agent_settings = [
            name
            for value, name in [
                (chat_agent_name, "foundry_chat_agent"),
                (product_agent_name, "foundry_product_agent"),
                (policy_agent_name, "foundry_policy_agent"),
            ]
            if not value
        ]
        if missing_agent_settings:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Azure AI Foundry agents are not fully configured. Missing or empty settings: "
                    + ", ".join(missing_agent_settings)
                ),
            )
        # Initialize result variable
        result = None

        # Importing here to avoid circular imports
        from ..utils.azure_credential_utils import get_azure_credential_async

        client_id = str(settings.azure_client_id) if settings.azure_client_id else None
        credential = await get_azure_credential_async(client_id=client_id)

        async with (
            credential,
            AIProjectClient(endpoint=ai_project_endpoint, credential=credential) as project_client,
            AzureAIProjectAgentProvider(
                project_client=project_client,
                credential=credential
            ) as provider,
        ):
            # Retry logic for rate limit errors (429 Too Many Requests)
            max_retries = 8
            default_retry_delay = 12  # seconds
            result = None

            # Retrieve product and policy agents in parallel
            product_agent, policy_agent = await asyncio.gather(
                provider.get_agent(name=product_agent_name),
                provider.get_agent(name=policy_agent_name),
            )

            # Tool para registrar oportunidades cuando el usuario comparte datos en el chat
            from ..tools import register_opportunity
            opportunity_tools = [register_opportunity] if register_opportunity else []

            for attempt in range(max_retries):
                try:
                    all_tools = [
                        product_agent.as_tool(name="product_agent"),
                        policy_agent.as_tool(name="policy_agent"),
                    ] + opportunity_tools
                    retrieved_agent = await provider.get_agent(
                        name=chat_agent_name,
                        tools=all_tools,
                    )
                    result = await retrieved_agent.run(question)
                    break  # Success, exit retry loop

                except Exception as e:
                    error_msg = str(e)
                    is_rate_limit = any(
                        kw in error_msg.lower()
                        for kw in ["rate limit", "exceeded", "retry after", "too many requests", "429"]
                    )

                    if is_rate_limit:
                        if attempt < max_retries - 1:
                            # Extract retry delay from error message (e.g., "retry after 4 seconds")
                            retry_match = re.search(r'retry after (\d+)', error_msg.lower())
                            retry_delay = int(retry_match.group(1)) + 1 if retry_match else default_retry_delay * (2 ** attempt)
                            logger.warning(f"Rate limit hit, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            # Final attempt - mensaje amigable para el usuario
                            logger.error(f"Rate limit retries exhausted: {error_msg}")
                            raise HTTPException(
                                status_code=429,
                                detail="El servicio está muy ocupado. Por favor espera 2-3 minutos antes de intentar de nuevo. Mientras tanto, puedes usar el botón «Registrar cotización» para guardar tus datos y un ejecutivo te contactará.",
                            )

                    # Non-rate-limit error: mensaje amigable para errores 500
                    logger.error(f"Error running AI agent: {e}", exc_info=True)
                    detail_msg = str(e)
                    if "429" in detail_msg or "too many" in detail_msg.lower():
                        raise HTTPException(
                            status_code=429,
                            detail="El servicio está muy ocupado. Por favor espera 2-3 minutos antes de intentar de nuevo. Mientras tanto, usa «Registrar cotización» para guardar tus datos.",
                        )
                    raise HTTPException(
                        status_code=500,
                        detail="Hubo un error al procesar tu mensaje. Por favor intenta de nuevo o usa el botón «Registrar cotización» para guardar tus datos directamente.",
                    )

        # Handle the result properly
        if result and hasattr(result, "text"):
            response_content = (result.text or "").strip()
        elif result:
            response_content = (str(result) or "").strip()
        else:
            raise HTTPException(status_code=500, detail="AI agent returned no response")

        # Fallback cuando el agente devuelve vacío (ej: índices AI Search vacíos, tool sin output)
        if not response_content:
            logger.warning("Agent returned empty response for question: %s", (message.content or "")[:100])
            response_content = (
                "No pude obtener información de nuestro catálogo en este momento. "
                "¿Puedes reformular tu pregunta o usar el botón «Registrar cotización» para que un ejecutivo te contacte?"
            )

        # Fallback: si el agente dice "No encontré" o da definición genérica, usar catálogo local
        resp_lower = response_content.lower()
        no_info_found = any(
            kw in resp_lower
            for kw in [
                "no encontré",
                "no logré obtener",
                "no logré",
                "no encontré esa información",
                "no encontré de inmediato",
                "no encontré información",
                "no encontré información específica",
                "usualmente, se refiere",
                "generalmente, se refiere",
                "generalmente se refiere",
            ]
        )
        user_msg = (message.content or "").strip()
        if no_info_found and user_msg:
            fallback = _get_product_fallback_response(message.content)
            if fallback:
                response_content = fallback
                logger.info("Fallback productos aplicado para: %s", user_msg[:60])

        # Post-proceso: eliminar filtración de prompt/instrucciones del agente
        response_content = _strip_leaked_instructions(response_content)

        # Post-proceso: si el usuario solo preguntó información (no cotización), quitar solicitud de contacto
        q_lower = user_msg.lower()
        wants_quote = any(
            kw in q_lower for kw in [
                "cotización", "cotizar", "cotiza", "contacten", "contacto",
                "contáctenme", "me interesa", "quiero que me", "presupuesto",
            ]
        )
        if not wants_quote and response_content:
            response_content = _remove_contact_prompt_for_informational(response_content)
            # Cierre solo si la respuesta es muy corta y no termina en puntuación
            r = response_content.rstrip()
            if response_content and len(response_content) < 100 and r and r[-1] not in ".?!":
                response_content += "\n\n¿Qué más necesitas saber?"

        # Si registramos desde confirmación pero el agente dice "problema", aclarar que sí se guardó
        if registered_from_confirmation and any(
            kw in response_content.lower() for kw in ["problema", "reenviar", "manualmente", "ocurrió"]
        ):
            response_content = (
                "¡Oportunidad registrada correctamente! Un ejecutivo de OPTI te contactará pronto. "
                + response_content
            )

        # Save AI response to Cosmos DB
        ai_response = ChatMessageCreate(
            content=response_content,
            message_type=ChatMessageType.ASSISTANT,
            metadata={"type": "ai_response"},
        )
        await get_chat_service().add_message_to_session(
            session_id, ai_response, user_id
        )

        return {
            "id": session_id,
            "content": response_content,
            "sender": "assistant",
            "timestamp": format_timestamp(datetime.utcnow()),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


@router.post("/sessions/new", response_model=APIResponse)
async def create_new_chat_session(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Create a new chat session"""
    try:
        user_id = current_user.get("user_id") if current_user else None

        # Create new session
        session_data = ChatSessionCreate(
            user_id=user_id,
            session_name=f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            context={},
        )

        session = await get_chat_service().create_chat_session(session_data)

        return APIResponse(
            message="New chat session created",
            data={
                "session_id": session.id,
                "session_name": session.session_name,
                "created_at": session.created_at.isoformat(),
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating new chat session: {str(e)}"
        )
