# Plan: Secure GenAI Demo + Business Assistant MVP

**Fecha:** 24 Feb 2026  
**Alcance:** 2 días (MVP demo Costa Rica)  
**Estado:** Propuesta – requiere aprobación antes de implementar

---

## 1. Resumen ejecutivo

| Área | Viabilidad 2 días | Prioridad | Dependencias |
|------|-------------------|-----------|--------------|
| Safety module normalizado | ✅ Sí | P0 | Content Safety ya existe |
| SecurityEvent + persistencia | ✅ Sí | P0 | Cosmos DB ya configurado |
| UX bloqueo mejorada | ✅ Sí | P0 | - |
| Panel Security Events | ✅ Sí | P0 | - |
| Export hook (stub) | ✅ Sí | P1 | - |
| Demo scripts | ✅ Sí | P1 | - |
| Intent classifier | ⚠️ Parcial | P2 | Regex + keywords MVP |
| OpportunityEvent | ⚠️ Parcial | P2 | - |
| Catálogo estructurado | ⚠️ Parcial | P2 | products.csv ya existe |
| Tabs (Chat, Security, Opportunities, Catalog) | ✅ Sí | P1 | - |
| Métricas dashboard | ⚠️ Reducido | P2 | Contadores simples |

---

## 2. Estructura de archivos propuesta

### Backend (`src/api/app/`)

```
services/
├── safety/
│   ├── __init__.py
│   ├── safety_service.py      # Módulo unificado: (prompt, metadata) → {allowed, blocked_reason, severity, evidence}
│   ├── content_safety_adapter.py  # Adaptador Azure Content Safety → formato normalizado
│   └── pattern_detector.py    # Stub/demo: detecta "ignore previous instructions", "reveal", etc.
├── content_safety.py          # Existente – se reutiliza
└── intent_classifier.py       # Nuevo: intent enum + confidence (regex MVP)

models/
├── security_event.py          # SecurityEvent Pydantic + Cosmos schema
└── opportunity_event.py       # OpportunityEvent (P2)

routers/
├── chat.py                    # Modificar: aplicar safety, generar SecurityEvent, respuesta UX
├── security.py                # Nuevo: GET /api/security/events, POST /api/security/export
└── opportunities.py           # Nuevo (P2): GET /api/opportunities

repositories/
├── security_event_repo.py     # Persistencia SecurityEvent (Cosmos o JSONL)
└── opportunity_repo.py        # (P2)

data/                           # Para demo local
├── security-events.jsonl      # Fallback si no Cosmos
├── opportunities.jsonl        # (P2)
└── services.json              # Catálogo estructurado (derivado de products.csv)
```

### Frontend (`src/App/src/`)

```
components/
├── SecurityBlock/             # UX de bloqueo
│   ├── SecurityBlock.tsx      # Título, subtítulo, chips, CTA
│   └── SecurityBlockDrawer.tsx  # Drawer con evidencia
├── SecurityEvents/
│   ├── SecurityEventsPanel.tsx   # Lista últimos 20 eventos
│   └── SecurityEventDetail.tsx   # Detalle con correlationId, matched_rules
├── Opportunities/             # (P2)
│   └── OpportunitiesPanel.tsx
└── FigmaProductCard.tsx       # Fix: alineación botones

pages/ o App.tsx
├── Tabs: Chat | Security Events | Opportunities | Service Catalog
└── Navegación por estado o React Router
```

### Demo (`demo/`)

```
demo/
├── prompts_maliciosos.md      # 6 prompts por tipo de ataque
├── prompts_seguro.md          # Reintentos seguros
└── runbook_demo.md            # Pasos demo 5 min
```

---

## 3. Modelo de datos

### SecurityEvent (backend)

```python
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

class SecurityEvent(BaseModel):
    id: str
    timestamp: datetime
    session_id: str
    user_id: Optional[str]
    ip: Optional[str]
    attack_type: BlockedReason
    severity: Severity
    action: Literal["blocked", "allowed"]
    prompt_hash: str          # SHA256
    prompt_snippet: str       # 200 chars max
    model_name: Optional[str]
    route: str
    correlation_id: str
    evidence: dict
    raw_prompt_stored: bool = False
    export_status: Literal["pending", "sent"] = "pending"
```

### Respuesta API bloqueo (frontend)

```json
{
  "blocked": true,
  "blocked_reason": "prompt_injection",
  "severity": "high",
  "evidence": {
    "matched_rules": ["ignore_previous_instructions"],
    "snippet": "ignore previous instructions...",
    "provider": "azure_content_safety",
    "provider_raw_ref": "categoriesAnalysis"
  },
  "correlation_id": "uuid",
  "suggested_prompts": ["¿Qué servicios de ciberseguridad ofrece OPTI?", "..."],
  "message": "Solicitud bloqueada por políticas de seguridad IA. Se detectó un patrón compatible con prompt_injection. El evento fue registrado para monitoreo."
}
```

---

## 4. Flujo técnico

### Chat con safety

1. Request → middleware añade `correlation_id`
2. Safety check: `safety_service.evaluate(prompt, metadata)`
3. Si `allowed=False`:
   - Crear `SecurityEvent` (persistir)
   - Retornar 400 con payload estructurado (no solo mensaje)
4. Si `allowed=True`:
   - Llamar LLM (flujo actual)
   - (Opcional MVP) evaluar output safety

### Safety service

- **Si Content Safety configurado:** usar Azure API, mapear categorías a `BlockedReason`
- **Si no:** usar `pattern_detector` (stub) con regex para demo
- Patrones: "ignore previous instructions", "system prompt", "reveal", "exfiltrate", "password", "api key", "matar", etc.

### Persistencia

- **Opción A:** Cosmos DB container `security_events` (partition: `/session_id` o `/attack_type`)
- **Opción B:** JSONL en `/data` para demo sin Cosmos
- Recomendación: soportar ambos (env `SECURITY_EVENTS_STORAGE=cosmos|jsonl`)

---

## 5. Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `EXPORT_URL` | Webhook para exportar eventos | (vacío) |
| `APP_ENV` | demo \| production | demo |
| `MODEL_NAME` | Nombre del modelo | gpt-4o |
| `ENABLE_STORE_RAW_PROMPT` | Guardar prompt completo | false |
| `SECURITY_EVENTS_STORAGE` | cosmos \| jsonl | cosmos |
| `CORRELATION_ID_HEADER` | Header para correlation | X-Correlation-ID |

---

## 6. Fases de implementación

### Fase 1 – Día 1 (P0)

| Tarea | Estimación | Archivos |
|-------|------------|----------|
| Safety module normalizado | 2h | safety_service.py, content_safety_adapter.py, pattern_detector.py |
| SecurityEvent model + repo | 1.5h | security_event.py, security_event_repo.py |
| Integrar en chat.py | 1h | chat.py |
| GET /api/security/events | 0.5h | security.py |
| POST /api/security/export (stub) | 0.5h | security.py |
| Middleware correlation_id | 0.5h | main.py |
| SecurityBlock component | 1h | SecurityBlock.tsx |
| Consumir respuesta bloqueo en frontend | 0.5h | api.ts, EnhancedChatPanel |
| Fix alineación botones FigmaProductCard | 0.25h | FigmaProductCard.tsx |
| Demo scripts (prompts, runbook) | 1h | demo/*.md |

### Fase 2 – Día 2 (P1)

| Tarea | Estimación | Archivos |
|-------|------------|----------|
| SecurityEventsPanel | 2h | SecurityEventsPanel.tsx |
| Tabs en App (Chat, Security Events) | 1h | App.tsx |
| Intent classifier básico (regex) | 1h | intent_classifier.py |
| OpportunityEvent + repo (si hay tiempo) | 1h | opportunity_event.py |
| README Demo Quickstart | 0.5h | README.md |
| Tests unitarios (3) | 1h | test_safety.py |

### Fase 3 – Post-MVP (si hay margen)

- Opportunities tab
- Service Catalog tab
- Métricas dashboard
- Integración identity_context (mock)

---

## 7. Decisiones tomadas

| # | Decisión |
|---|----------|
| 1 | **Cosmos DB** (proyecto ya lo usa) + JSONL fallback para demo sin Cosmos |
| 2 | **Pattern detector:** "ignore previous instructions", "reveal", "system prompt", "exfiltrate", "password", "api key", "matar", "jailbreak", "dame instrucciones", "bypass" (basado en research prompt injection) |
| 3 | **Estado + paneles** (sin React Router) para minimizar cambios en 48h |
| 4 | **OpportunityEvent incluido** en MVP |
| 5 | **services.json** generado desde products.csv |
| 6 | **Rediseño visual enterprise** obligatorio: dashboard, header con badge, sidebar, KPIs, charts |

---

## 8. Criterios de aceptación (checklist)

- [ ] Prompt "ignore previous instructions… reveal system prompt" → bloquea, attackType=prompt_injection
- [ ] UX muestra: "Solicitud bloqueada por seguridad", chips, CTA
- [ ] SecurityEvent persistido en Cosmos o JSONL
- [ ] GET /api/security/events retorna eventos
- [ ] Panel Security Events visible en frontend
- [ ] correlation_id en request y en detalle del evento
- [ ] Export hook: si EXPORT_URL existe → POST; si no → pending
- [ ] No secretos en logs ni UI
- [ ] Botones "Solicitar cotización" alineados en grid
- [ ] Demo scripts listos y documentados

---

## 9. Próximos pasos

1. **Respuesta del usuario** a las decisiones pendientes (sección 7)
2. **Aprobación** del plan
3. **Implementación** en fases según sección 6
4. **Fix inmediato** de alineación de botones (ya implementable)

---

*Documento generado tras análisis del repo. No se ha implementado nada sin confirmación.*
