# Pattern detector for prompt injection, jailbreak, data exfiltration (demo/stub)
# Basado en: OWASP LLM Top 10, research prompt injection 2024

import re
from enum import Enum
from typing import Optional

# ── JAILBREAK — patrones elaborados (DAN, rol, bypass, extracción de prompt) ─────
_JAILBREAK_EXTRA = [
    r"(?i)\bDAN\b.*do\s+anything\s+now",
    r"(?i)a\s+partir\s+de\s+ahora\s+eres\s+DAN",
    r"(?i)eres?\s+(ahora\s+)?(un\s+)?(asistente?\s+)?sin\s+(filtros?|restricciones?)",
    r"(?i)you\s+are\s+now\s+an?\s+unrestricted",
    r"(?i)act\s+as\s+(if\s+you\s+(have\s+no|are\s+free\s+from)|an?\s+unrestricted)",
    r"(?i)no\s+tiene\s+restricciones\s+de\s+seguridad",
    r"(?i)puede\s+responder\s+cualquier\s+pregunta\s+sin",
    r"(?i)vamos\s+a\s+jugar\s+un\s+juego\s+de\s+rol",
    r"(?i)juego\s+de\s+rol.*sin\s+(filtros?|restricciones?)",
    r"(?i)forget\s+(you\s+are|your\s+(instructions?|constraints?|role))",
    r"(?i)forget\s+all\s+(previous\s+)?instructions",
    r"(?i)ignore\s+(all\s+)?(previous|prior|your)\s+instructions",
    r"(?i)olvida\s+(todas?\s+(las?\s+)?)?instrucciones",
    r"(?i)disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"(?i)bypass\s+(your\s+)?(safety|filters?|restrictions?|guidelines?|content.?policy)",
    r"(?i)saltarte?\s+(los?\s+)?(filtros?|restricciones?|seguridad)",
    r"(?i)desactiv[ae]\s+(los?\s+)?(filtros?|restricciones?|seguridad)",
    r"(?i)disable\s+(your\s+)?(safety|filters?|restrictions?)",
    r"(?i)(dame|muestra|revela|show|reveal|display)\s+(el\s+)?prompt\s+oculto",
    r"(?i)(dame|muestra|revela|show|reveal|display)\s+(el\s+)?system\s+prompt",
    r"(?i)(dame|muestra|revela)\s+(las?\s+)?instrucciones\s+del?\s+sistema",
    r"(?i)(what\s+are|show\s+me)\s+your\s+(system\s+prompt|instructions|constraints)",
    r"(?i)reveal\s+your\s+(prompt|instructions|system)",
    r"(?i)(est[aá]s?\s+en|modo|activar?)\s+(modo\s+)?(depuraci[oó]n|debug|developer)",
    r"(?i)developer\s+mode\s+(enabled|activated|on)",
    r"(?i)\bdan\s+mode\b",
    r"(?i)\bgodmode\b",
    r"(?i)\bunrestricted\s+mode\b",
    r"(?i)system\s+override",
    r"(?i)nivel\s+de\s+acceso[:\s]+administrador",
    r"(?i)jailbreak\s+(autorizado|test|prueba)",
    r"(?i)authorized\s+by\s+(the\s+)?(security\s+team|admin)",
    r"(?i)ignora\s+(todas?\s+(tus?\s+)?)?instrucciones.{0,80}(api.?key|credencial|contraseña|password|cosmos|connection.?string)",
    r"(?i)(bypass|ignore|forget).{0,100}(system.?prompt|api.?key|source.?code|credencial)",
    r"(?i)nuevo\s+objetivo[:\s].{0,60}(system.?prompt|api.?key|credencial|base\s+de\s+datos)",
    r"(?i)modo\s+de\s+depuraci[oó]n.{0,100}(api.?key|credencial|source.?code|contraseña)",
]

# ── ADMIN IMPERSONATION — suplantación de administrador / auditoría falsa ───────────
_ADMIN_IMPERSONATION_EXTRA = [
    r"(?i)administrador\s+global",
    r"(?i)(ya\s+fue|ha\s+sido)\s+autenticado\s+como\s+administrador",
    r"(?i)configuraci[oó]n\s+interna\s+del\s+entorno",
    r"(?i)clave\s+asociada",
    r"(?i)ignorar?\s+las?\s+reglas\s+de\s+seguridad",
    r"(?i)prompt\s+oculto\s+del\s+sistema",
    r"(?i)auditor[ií]a.{0,50}ignora",
    r"(?i)este\s+mensaje\s+proviene\s+del\s+administrador",
    r"(?i)validaci[oó]n\s+administrativa",
    r"(?i)contexto\s+de\s+seguridad\s+actualizado",
    r"(?i)reconfigurado\s+por\s+el\s+equipo\s+de\s+TI",
    r"(?i)nueva\s+pol[ií]tica[:\s].{0,40}ignora",
    r"(?i)ignora\s+(cualquier\s+)?restricci[oó]n\s+anterior",
    r"(?i)SELECT\s+\*.{0,60}(usuarios?|users?|passwords?|tokens?)",
]

# Patrones de prompt injection y jailbreak (research: IBM, Anthropic, OWASP)
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"forget\s+(everything|all)\s+(you\s+)?(were\s+)?(told|learned)",
    r"olvida\s+(todo|todas?\s+las?\s+instrucciones)",
    r"olvides?\s+(todo|todas?\s+las?\s+instrucciones)",
    r"override\s+(your\s+)?(instructions|system\s+prompt)",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*you\s+are",
    r"you\s+are\s+now\s+(a|in)\s+",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+if\s+you",
    r"bypass\s+(your\s+)?(safety|restrictions|guidelines)",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
    r"modo\s+desarrollador",
    r"dame\s+(las\s+)?instrucciones\s+(del\s+)?sistema",
    r"revela\s+(el\s+)?(prompt|sistema)",
    r"muestra\s+(el\s+)?(prompt|sistema)",
    r"eres\s+(un\s+)?(amigo|amiga|sin\s+restricciones)",
    r"imagine\s+you\s+are\s+(a|un)\s+",
    # Suplantación de administrador / auditoría falsa
    r"administrador\s+del\s+sistema",
    r"admin\s+del\s+sistema",
    r"ignorar\s+(las\s+)?reglas\s+(de\s+)?seguridad",
    r"ignore\s+(the\s+)?security\s+rules",
    r"prompt\s+oculto\s+(del\s+)?sistema",
    r"hidden\s+system\s+prompt",
    r"configuración\s+interna",
    r"internal\s+configuration",
    r"ignora\s+cualquier\s+restricción",
    r"ignore\s+any\s+restriction",
    r"validación\s+administrativa",
    r"administrative\s+validation",
    r"autenticado\s+como\s+administrador",
    r"authenticated\s+as\s+administrator",
    r"administrador\s+global",
    r"global\s+administrator",
    r"clave\s+asociada",
    r"associated\s+key",
] + _ADMIN_IMPERSONATION_EXTRA

# Jailbreak: palabra exacta + patrones elaborados
JAILBREAK_PATTERNS = [r"(?i)\bjailbreak\b"] + _JAILBREAK_EXTRA

# Patrones de revelación de secretos / data exfiltration
DATA_EXFIL_PATTERNS = [
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"show\s+(me\s+)?(your\s+)?(system\s+)?prompt",
    r"what\s+(are\s+)?(your\s+)?(initial\s+)?instructions",
    r"exfiltrate",
    r"exfiltrar",
    r"dame\s+(el\s+)?código\s+fuente",
    r"dame\s+información\s+(de\s+)?(las\s+)?tarjetas\s+de\s+crédito",
    r"código\s+fuente",
    r"código\s+de\s+(la\s+)?(app|aplicación)",
    r"source\s+code",
    r"olvides?\s+.*código",
    r"olvida\s+.*código",
    r"password",
    r"api\s+key",
    r"secret\s+key",
    r"access\s+token",
    r"credentials?",
    r"contraseña",
    r"clave\s+(api|secreta)",
    # Catálogo / estructura interna
    r"catálogo\s+interno",
    r"internal\s+(service\s+)?catalog",
    r"service\s+catalog\s+metadata",
    r"estructura\s+completa\s+.*json",
    r"campos\s+ocultos",
    r"hidden\s+fields",
    r"metadata\s+intern[ao]",
    r"internal\s+metadata",
]

# Patrones de violencia (Content Safety complement)
VIOLENCE_PATTERNS = [
    r"matar\s+(a\s+)?(alguien|algo|a)",
    r"quiero\s+matar",
    r"quiero\s+morir",
    r"suicid",
    r"kill\s+(yourself|someone|me|him|her)",
    r"hurt\s+(yourself|someone|me)",
    r"violence",
    r"violencia",
    r"ideas?\s+para\s+robar",
    r"how\s+to\s+(kill|hurt|murder)",
    r"cómo\s+matar",
    r"cómo\s+herir",
]

# Patrones de credential theft
CREDENTIAL_THEFT_PATTERNS = [
    r"dame\s+(las?\s+)?contraseñas?",
    r"dame\s+(la\s+)?clave",
    r"dame\s+(el\s+)?password",
    r"cual\s+es\s+(la\s+)?contraseña",
    r"reveal\s+(passwords?|credentials?)",
    r"steal\s+(credentials?|tokens?)",
    r"phishing",
]


class BlockedReason(str, Enum):
    violence = "violence"
    self_harm = "self_harm"
    hate = "hate"
    sexual = "sexual"
    prompt_injection = "prompt_injection"
    jailbreak = "jailbreak"
    data_exfiltration = "data_exfiltration"
    credential_theft = "credential_theft"
    other = "other"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


def detect_patterns(text: str) -> tuple[Optional[BlockedReason], Severity, list[str]]:
    """Detecta patrones maliciosos. Retorna (reason, severity, matched_rules)."""
    if not text or not text.strip():
        return None, Severity.low, []

    text_lower = text.lower().strip()
    matched = []

    # Jailbreak (DAN, rol sin filtros, bypass, extracción de prompt, etc.)
    for pat in JAILBREAK_PATTERNS:
        if re.search(pat, text, re.IGNORECASE | re.DOTALL):
            matched.append(f"jailbreak:{pat[:40]}...")
            return BlockedReason.jailbreak, Severity.high, matched

    # Prompt injection / admin impersonation
    for pat in PROMPT_INJECTION_PATTERNS:
        if re.search(pat, text, re.IGNORECASE | re.DOTALL):
            matched.append(f"prompt_injection:{pat[:30]}...")
            return BlockedReason.prompt_injection, Severity.high, matched

    # Data exfiltration
    for pat in DATA_EXFIL_PATTERNS:
        if re.search(pat, text_lower, re.IGNORECASE):
            matched.append(f"data_exfil:{pat[:30]}...")
            return BlockedReason.data_exfiltration, Severity.high, matched

    # Credential theft
    for pat in CREDENTIAL_THEFT_PATTERNS:
        if re.search(pat, text_lower, re.IGNORECASE):
            matched.append(f"cred_theft:{pat[:30]}...")
            return BlockedReason.credential_theft, Severity.high, matched

    # Violence / self-harm
    for pat in VIOLENCE_PATTERNS:
        if re.search(pat, text_lower, re.IGNORECASE):
            matched.append(f"violence:{pat[:30]}...")
            if "morir" in text_lower or "suicid" in text_lower or "yourself" in text_lower:
                return BlockedReason.self_harm, Severity.high, matched
            return BlockedReason.violence, Severity.high, matched

    return None, Severity.low, []
