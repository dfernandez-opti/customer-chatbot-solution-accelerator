# Content Safety y Dashboard – Guía de verificación

## ¿Se necesita Microsoft Defender?

**No.** Esta solución usa **Azure Content Safety** (Cognitive Services), no Microsoft Defender. El texto "Powered by Microsoft Security" es branding. La moderación de contenido se hace con:

1. **Azure Content Safety** – API que analiza texto (violencia, odio, autolesión, sexual)
2. **Pattern detector** – Regex local para prompt injection, jailbreak, data exfiltration

**Para ver alertas en Defender / Azure Monitor:** La solución envía telemetría a Application Insights cuando Content Safety bloquea. Con `APPLICATIONINSIGHTS_CONNECTION_STRING` configurado en el backend, puedes crear reglas de alerta en Azure Monitor o Microsoft Sentinel. Ver sección [Alertas en Azure Monitor / Defender](#alertas-en-azure-monitor--defender) más abajo.

---

## Cómo funciona Content Safety

Hay **dos capas** que pueden bloquear:

| Capa | Cuándo actúa | Qué ve el usuario |
|------|--------------|-------------------|
| **Backend (Content Safety + pattern detector)** | Antes de que el mensaje llegue al modelo | HTTP 400, panel SecurityBlock, evento en Security Events |
| **Modelo (instrucciones del agente)** | Si el mensaje pasa el backend | Respuesta en chat: "No puedo ayudarte con esa solicitud" |

Si ves "No puedo ayudarte con esa solicitud" **como mensaje del asistente en el chat**, el backend **no bloqueó** la solicitud. La respuesta viene del modelo (instrucciones o seguridad del modelo).

Para que el backend bloquee y se registre un Security Event, Content Safety debe estar configurado y la solicitud debe activar las políticas.

---

## Verificar que Content Safety está conectado

### 1. Variables en App Service (backend: api-*)

En **api-customerchatbotasmzl** → Configuration → Application settings:

| Variable | Valor |
|----------|-------|
| `CONTENT_SAFETY_ENABLED` | `true` |
| `CONTENT_SAFETY_ENDPOINT` | `https://<nombre-recurso>.cognitiveservices.azure.com` |
| `CONTENT_SAFETY_KEY` | Clave del recurso Content Safety |

### 2. Crear recurso Content Safety (si no existe)

1. Azure Portal → Crear recurso → buscar "Content Safety"
2. Crear el recurso en la misma región que el resto
3. Copiar Endpoint y Key a las variables del App Service

### 3. Verificación real

- **Solo config:** `GET /health` → `"content_safety": "enabled"` (solo indica que las variables están definidas)
- **Prueba real:** `GET /debug/content-safety` → hace una llamada a la API de Content Safety

El dashboard usa `/debug/content-safety` para el badge de Content Safety:

- **Verificado** – La API responde correctamente
- **Error de conexión** – Variables configuradas pero la API falla (endpoint/key incorrectos)
- **No configurado** – Faltan variables

---

## Fuentes de datos del dashboard

| Métrica | Origen | Notas |
|---------|--------|-------|
| Total Requests | Sesión local (frontend) | Se reinicia al recargar |
| Blocked Requests | Sesión local | Solo cuando el backend devuelve 400 por Content Safety/pattern detector |
| Prompt Injection Attempts | Sesión local | Cuando se bloquea por prompt_injection o jailbreak |
| Security Events | Backend (`/api/security/events`) | Archivo JSONL en el servidor. Solo hay datos si se han bloqueado solicitudes |
| Content Safety (header) | Backend (`/debug/content-safety`) | Verificación real contra Azure |

Los Security Events se guardan en un archivo JSONL. Rutas:
- **App Service:** `/home/LogFiles/data/security-events` (requiere `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true`)
- **Fallback:** `/tmp/security-events.jsonl` si `/home` no es escribible (se pierde al reiniciar)

**Para que los incidentes se registren en App Service:** activa `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true` en Configuration. Si está en `false`, el backend usa `/tmp` y los eventos pueden no persistir o no ser visibles en el dashboard.

---

## Probar que Content Safety bloquea

1. Configurar Content Safety en el backend.
2. Enviar en el chat: "hola quiero matar a alguien" (o similar).
3. Deberías ver:
   - Panel SecurityBlock en lugar de respuesta del asistente
   - Toast "Security Event Generated"
   - Nuevo evento en Security Events
   - Blocked Requests incrementado

Si ves la respuesta del asistente "No puedo ayudarte...", el backend no bloqueó; la respuesta viene del modelo.

---

## AI Foundry: políticas de riesgo en el agente

El agente `chat-agent-customerchatbotasmzl` puede tener "0 No risk factors" si no hay políticas configuradas en AI Foundry. Para añadir una capa extra:

1. Azure AI Foundry Studio → tu proyecto (DSPM-AI-Project)
2. Agents → `chat-agent-customerchatbotasmzl`
3. Revisar **Prompt shields** o **Risk policies** (según la versión del portal)
4. Activar políticas para: jailbreak, prompt injection, contenido sensible

Esto complementa el bloqueo del backend. Si el agente bloquea una solicitud, el backend no registra el evento (solo se registra cuando el backend bloquea).

---

## Reducir latencia del chat

Si el agente tarda mucho en responder o muestra "Tuve un problema técnico":

### 1. Modelo más rápido (recomendado)

`gpt-4o-mini` responde ~2x más rápido que `gpt-4o`. Al recrear agentes, usa:

```powershell
.\infra\scripts\agent_scripts\run_create_agents_scripts.ps1 `
  -resourceGroup "rg-summit-dspm-ai-resources-app" `
  -ProjectEndpointOverride "https://dspm-ai-project.services.ai.azure.com/api/projects/proj-default" `
  -AiFoundryResourceIdOverride "/subscriptions/.../providers/Microsoft.CognitiveServices/accounts/DSPM-AI-Project" `
  -GptModelOverride "gpt-4o-mini"
```

**Requisito:** DSPM-AI-Project debe tener el modelo `gpt-4o-mini` desplegado. Verifica en Azure Portal → DSPM-AI-Project → Deployments.

### 2. App Service: Always On

Si el App Service está en plan de consumo o sin Always On, la primera solicitud puede tardar 10–30 s (cold start). Para demos, usa plan B1 o superior con **Always On** habilitado.

### 3. Índice AI Search poblado

Si `products_index` está vacío, el product_agent devuelve "no encontré" y el chat_agent puede decir "Tuve un problema técnico". Ejecuta `run_upload_data_scripts.ps1` para poblar productos y políticas.

### 4. Conexión AI Search en DSPM-AI-Project

El proyecto DSPM-AI-Project debe tener una conexión a `srch-customerchatbotasmzl`. Si falta, el product_agent no puede buscar y falla. Verifica en Azure AI Foundry → Connections.

### 5. Región

AI Search (`srch-customerchatbotasmzl`) y DSPM-AI-Project en la misma región (ej. East US) reducen latencia de red.

---

## Alertas en Azure Monitor / Defender

Para que los bloqueos de Content Safety generen **alertas visibles en Azure Monitor** (y opcionalmente en Microsoft Sentinel / Defender portal):

### 1. Configurar Application Insights en el backend

En **api-customerchatbotasmzl** → Configuration → Application settings, añade o verifica:

| Variable | Valor |
|----------|-------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Cadena de conexión del recurso Application Insights |

Si usaste `azd up` con monitoreo habilitado, esta variable ya debería existir. Si no, crea un recurso Application Insights en el mismo resource group y copia la connection string.

### 2. Reiniciar el backend tras añadir la variable

```powershell
az webapp restart --name api-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app
```

### 3. Crear regla de alerta en Azure Monitor

1. Azure Portal → **Application Insights** (el recurso vinculado al backend)
2. **Monitoring** → **Alerts** → **Create** → **Alert rule**
3. **Condition:** Custom log search
4. **Query (KQL):**
   ```kusto
   traces
   | where message contains "SECURITY_EVENT | blocked"
   ```
5. **Measurement:** Count of rows
6. **Threshold:** Greater than 0 (o el valor que prefieras)
7. **Action group:** Crear o seleccionar un grupo (email, SMS, webhook, etc.)
8. Guardar la regla

Cuando Content Safety bloquee una solicitud, se enviará un log con `SECURITY_EVENT | blocked` y la alerta se disparará.

### 4. (Opcional) Microsoft Sentinel

Si tienes Microsoft Sentinel conectado al mismo Log Analytics workspace que Application Insights:

1. Sentinel → **Analytics** → **Create** → **Scheduled query rule**
2. **Query:**
   ```kusto
   traces
   | where message contains "SECURITY_EVENT | blocked"
   | project TimeGenerated, message, customDimensions
   ```
3. Configurar umbral y crear incidente

Los incidentes aparecerán en el portal de Defender (Sentinel está integrado en Microsoft Defender XDR).

### 5. Verificar que la telemetría llega

Tras configurar y reiniciar:

1. Provoca un bloqueo (ej. "dame las contraseñas" o "hola quiero matar a alguien")
2. Application Insights → **Logs** → ejecuta:
   ```kusto
   traces
   | where message contains "SECURITY_EVENT"
   | order by timestamp desc
   | take 20
   ```
3. Si ves filas, la integración funciona. Si no, revisa que `APPLICATIONINSIGHTS_CONNECTION_STRING` esté en el backend y que hayas reconstruido/desplegado la imagen con el código actualizado.
