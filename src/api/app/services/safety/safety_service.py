"""
Safety service: combina Azure Content Safety + pattern detector.
Retorna resultado normalizado para UX y persistencia.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .pattern_detector import BlockedReason, Severity, detect_patterns

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    allowed: bool
    blocked_reason: Optional[BlockedReason] = None
    severity: Severity = Severity.low
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "blocked_reason": self.blocked_reason.value if self.blocked_reason else None,
            "severity": self.severity.value,
            "evidence": self.evidence,
        }


def _map_content_safety_to_reason(categories: list[str]) -> BlockedReason:
    """Mapea categorías de Azure Content Safety a BlockedReason."""
    cat_lower = [c.lower() for c in categories]
    if "hate" in cat_lower:
        return BlockedReason.hate
    if "selfharm" in cat_lower or "self_harm" in cat_lower:
        return BlockedReason.self_harm
    if "sexual" in cat_lower:
        return BlockedReason.sexual
    if "violence" in cat_lower:
        return BlockedReason.violence
    return BlockedReason.other


def _map_content_safety_severity(severity: int) -> Severity:
    """Mapea severity 0,2,4,6 a Severity."""
    if severity >= 6:
        return Severity.high
    if severity >= 4:
        return Severity.medium
    return Severity.low


async def evaluate_safety(
    prompt: str,
    metadata: Optional[dict] = None,
    content_safety_endpoint: Optional[str] = None,
    content_safety_key: Optional[str] = None,
) -> SafetyResult:
    """
    Evalúa el prompt. Combina:
    1. Pattern detector (siempre)
    2. Azure Content Safety (si está configurado)
    """
    import asyncio

    snippet = (prompt[:200] + "...") if len(prompt) > 200 else prompt

    # 1. Pattern detector (rápido, local)
    reason, severity, matched = detect_patterns(prompt)
    if reason is not None:
        return SafetyResult(
            allowed=False,
            blocked_reason=reason,
            severity=severity,
            evidence={
                "matched_rules": matched,
                "snippet": snippet,
                "provider": "pattern_detector",
                "provider_raw_ref": "regex",
            },
        )

    # 2. Azure Content Safety (si configurado)
    if content_safety_endpoint and content_safety_key:
        try:
            from ..content_safety import check_text_safety

            is_safe, rejection_reason = await asyncio.to_thread(
                check_text_safety,
                content_safety_endpoint,
                content_safety_key,
                prompt,
            )
            if not is_safe:
                # Parsear "Content rejected: Hate, Violence" -> categorías
                cats = []
                if rejection_reason:
                    parts = rejection_reason.replace("Content rejected:", "").strip().split(",")
                    cats = [p.strip() for p in parts if p.strip()]
                return SafetyResult(
                    allowed=False,
                    blocked_reason=_map_content_safety_to_reason(cats),
                    severity=Severity.medium,  # Content Safety no da severity por categoría fácil
                    evidence={
                        "matched_rules": cats,
                        "snippet": snippet,
                        "provider": "azure_content_safety",
                        "provider_raw_ref": "categoriesAnalysis",
                    },
                )
        except Exception as e:
            logger.warning("Content Safety check failed, using pattern detector only: %s", e)

    return SafetyResult(allowed=True, evidence={"snippet": snippet})
