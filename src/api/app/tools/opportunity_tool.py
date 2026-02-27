# Copyright (c) Microsoft Corporation.
# Tool para que el agente registre oportunidades cuando el usuario comparte sus datos en el chat.

from typing import Annotated, Optional

from pydantic import Field

# Import condicional para evitar circular
try:
    from agent_framework import tool
except ImportError:
    tool = None  # Fallback si no está instalado

from ..repositories.opportunity_repo import create_opportunity


def _register_opportunity_impl(
    contact_name: Optional[str],
    email: Optional[str],
    phone: str,
    company: str,
    service: str,
) -> str:
    """Registra una oportunidad de cotización en el sistema."""
    try:
        opp = create_opportunity(
            phone=phone,
            company=company,
            service=service,
            contact_name=contact_name or None,
            email=email or None,
        )
        return (
            f"Oportunidad registrada correctamente. ID: {opp['id']}. "
            "Un ejecutivo de OPTI contactará al cliente."
        )
    except Exception as e:
        return f"Error al registrar la oportunidad: {str(e)}"


if tool:

    @tool(
        name="register_opportunity",
        description=(
            "Registra una oportunidad de cotización cuando el usuario comparte sus datos de contacto "
            "(nombre, correo, teléfono, empresa, servicio de interés). Usa esta herramienta SOLO cuando "
            "el usuario haya proporcionado al menos: teléfono, empresa y servicio. Si falta algún dato, "
            "pide el que falte antes de llamar a la herramienta."
        ),
        approval_mode="never_require",
    )
    def register_opportunity(
        contact_name: Annotated[
            str,
            Field(description="Nombre completo del contacto o cliente"),
        ] = "",
        email: Annotated[
            str,
            Field(description="Correo electrónico del cliente"),
        ] = "",
        phone: Annotated[
            str,
            Field(description="Teléfono del cliente (obligatorio)"),
        ] = "",
        company: Annotated[
            str,
            Field(description="Nombre de la empresa del cliente (obligatorio)"),
        ] = "",
        service: Annotated[
            str,
            Field(
                description="Servicio de interés: IA, BRE, SEC, ITSM, CSP, Cloud and Data, Servicios Administrados, Seguridad Integral, etc."
            ),
        ] = "",
    ) -> str:
        """Registra oportunidad cuando el usuario comparte datos de contacto."""
        if not phone or not company or not service:
            return (
                "Faltan datos obligatorios. Para registrar la oportunidad necesito: "
                "teléfono, empresa y servicio de interés. ¿Puedes compartirlos?"
            )
        return _register_opportunity_impl(
            contact_name=contact_name or None,
            email=email or None,
            phone=phone,
            company=company,
            service=service,
        )

else:
    register_opportunity = None
