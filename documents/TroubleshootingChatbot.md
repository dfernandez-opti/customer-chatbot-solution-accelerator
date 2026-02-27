# Solución: El chatbot no responde

## 1. Revisar variables del BACKEND (API)

La imagen que viste es del **frontend** (`app-customerchatbotasmzl`). El chatbot corre en el **backend** (`api-customerchatbotasmzl`).

**En Azure Portal:**
1. Ve al App Service **api-customerchatbotasmzl** (no el app-)
2. Configuración → **Environment variables**
3. Comprueba que existan estas variables:

| Variable | Descripción |
|----------|-------------|
| `AZURE_FOUNDRY_ENDPOINT` | URL del proyecto AI Foundry |
| `FOUNDRY_CHAT_AGENT` | Nombre del agente de chat (debe tener valor) |
| `FOUNDRY_PRODUCT_AGENT` | Nombre del agente de productos |
| `FOUNDRY_POLICY_AGENT` | Nombre del agente de políticas |
| `COSMOS_DB_ENDPOINT` | URL de Cosmos DB |
| `AZURE_SEARCH_ENDPOINT` | URL de Azure AI Search |
| `AZURE_SEARCH_INDEX` | Índice de políticas |
| `AZURE_SEARCH_PRODUCT_INDEX` | Índice de productos |

**Content Safety (alertas por contenido indebido):** ⚠️ **Deben estar en el BACKEND (api-), no en el frontend**

| Variable | Descripción |
|----------|-------------|
| `CONTENT_SAFETY_ENABLED` | `true` para activar moderación |
| `CONTENT_SAFETY_ENDPOINT` | URL del recurso (ej. `https://app-customerchatbotasmzl-contentsafety.cognitiveservices.azure.com`) |
| `CONTENT_SAFETY_KEY` | Clave del recurso Content Safety |

**Verificar:** `https://api-customerchatbotasmzl.azurewebsites.net/health` debe mostrar `"content_safety": "enabled"`.

Si Content Safety está activo, los mensajes que violen políticas (odio, autolesión, contenido sexual, violencia) se rechazan y se registra un evento en logs (`SECURITY_EVENT | blocked`). Para ver alertas en Defender/Azure Monitor, configura `APPLICATIONINSIGHTS_CONNECTION_STRING` en el backend y crea una regla de alerta. Ver `documents/ContentSafetyYDashboard.md` sección "Alertas en Azure Monitor / Defender".

**Si no funciona:**
1. Comprueba que las 3 variables estén en **api-customerchatbotasmzl** (Configuration → Application settings).
2. **Reconstruye y despliega el backend** (obligatorio para que el código de Content Safety esté en la imagen):
   ```powershell
   .\scripts\build-and-push.ps1 -AcrName optisummitacr -ImageTag opti-summit
   az webapp restart --name api-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app
   ```
3. Verifica: `https://api-customerchatbotasmzl.azurewebsites.net/health` debe mostrar `"content_safety": "enabled"`.
4. Diagnóstico: `https://api-customerchatbotasmzl.azurewebsites.net/debug/content-safety` muestra si la API de Content Safety responde correctamente.

**Si `FOUNDRY_CHAT_AGENT`, `FOUNDRY_PRODUCT_AGENT` o `FOUNDRY_POLICY_AGENT` están vacíos**, hay que ejecutar el script de agentes.

**Si eliminaste el policy agent:** Ejecuta `run_create_agents_scripts.ps1` para recrearlo. El policy agent busca políticas, garantías y procedimientos de OPTI en el índice `policies_index`.

---

## 9a. El chat pide contacto en preguntas informativas

**Síntomas:** Preguntas como "¿qué es CSP?" o "¿qué servicios de ciberseguridad tienen?" devuelven la descripción pero siempre terminan con "¿Te gustaría que te contactemos? Comparte tu nombre, correo, teléfono y empresa."

**Solución:**

1. **El backend ya post-procesa** las respuestas: si el usuario no pidió cotización, se quita la solicitud de contacto. Reconstruye y despliega el backend para que los cambios surtan efecto.
2. **Recrear agentes** (opcional, para que el agente mismo no genere esa solicitud): ejecuta `.\infra\scripts\agent_scripts\run_create_agents_scripts.ps1` con el resource group correcto. Los agentes se actualizan con instrucciones que no piden contacto en preguntas informativas.

---

## 9b. El chat no trae información de soluciones/productos

**Síntomas:** Preguntas como "¿Qué es CSP?" o "Quiero cotización para Servicios Administrados" devuelven "No encontré esa información" aunque los índices tienen datos.

**Causas y soluciones:**

1. **query_type inválido:** Los agentes usaban `vector_simple` (no soportado). Se cambió a `vector_simple_hybrid` para combinar búsqueda vectorial + keyword.
2. **Campo content no searchable:** Para hybrid search, el campo `content` debe ser searchable. Se actualizaron los scripts de creación de índices.
3. **Recrear agentes y recargar datos:** Tras los cambios, ejecuta:
   ```powershell
   # 1. Recargar índices (recrea con content searchable)
   .\infra\scripts\data_scripts\run_upload_data_scripts.ps1 -resource_group "rg-summit-dspm-ai-resources-app"
   
   # 2. Recrear agentes (con vector_simple_hybrid)
   .\infra\scripts\agent_scripts\run_create_agents_scripts.ps1 -resourceGroup "rg-summit-dspm-ai-resources-app"
   
   # 3. Reiniciar API
   az webapp restart --name api-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app
   ```

---

## 9c. Error "No tool output found for function call"

**Síntomas:** El chat muestra un error rojo: "No tool output found for function call call_XXX". El agente no responde con información.

**Causa:** El product_agent o policy_agent llamó a Azure AI Search pero la herramienta no devolvió resultado. Suele ocurrir cuando:
1. Los índices `products_index` y `policies_index` están **vacíos**
2. La conexión a AI Search tiene problemas de permisos
3. El índice no tiene el esquema correcto (campo vector para búsqueda)

**Solución:**

1. **Subir datos a AI Search** (obligatorio):
   ```powershell
   .\infra\scripts\data_scripts\run_upload_data_scripts.ps1 -resource_group "rg-summit-dspm-ai-resources-app"
   ```
   Este script crea los índices y carga productos y políticas de OPTI.

2. **Verificar permisos:** El proyecto Foundry (DSPM-AI-Project) debe tener rol "Search Index Data Reader" en el recurso de AI Search. Si usaste el deployment con conexión existente, debería estar configurado.

3. **Probar en la app, no solo en el playground:** El error puede aparecer en el playground de Foundry. Prueba en `https://app-customerchatbotasmzl.azurewebsites.net` donde el backend tiene más control.

---

## 2. az CLI falla con PermissionError (purview)

**Síntoma:** `az` falla con `Permission denied: ...\purview\azext_metadata.json`. Afecta a `run_create_agents_scripts.ps1`, `az login`, etc.

**Solución rápida:**
```powershell
.\scripts\fix-az-purview.ps1
```
O manualmente: elimina la carpeta `%USERPROFILE%\.azure\cliextensions\purview`.

Tras eso, `az` y `run_create_agents_scripts.ps1` deberían funcionar.

---

## 3. Ejecutar scripts post-despliegue

Desde la raíz del proyecto:

```powershell
cd customer-chatbot-solution-accelerator
```

**Paso 1 – Cargar datos (productos OPTI, políticas):**
```powershell
.\infra\scripts\data_scripts\run_upload_data_scripts.ps1 -resource_group "rg-summit-dspm-ai-resources-app"
```

**Paso 2 – Crear agentes y actualizar variables del backend:**
```powershell
.\infra\scripts\agent_scripts\run_create_agents_scripts.ps1 -resourceGroup "rg-summit-dspm-ai-resources-app"
```

Este script crea los agentes en AI Foundry y actualiza `FOUNDRY_CHAT_AGENT`, `FOUNDRY_PRODUCT_AGENT` y `FOUNDRY_POLICY_AGENT` en el App Service del backend.

---

## 3. Revisar variables del frontend

En `app-customerchatbotasmzl` debe estar:

| Variable | Valor esperado |
|----------|----------------|
| `VITE_API_BASE_URL` | `https://api-customerchatbotasmzl.azurewebsites.net` |

Si el backend tiene otro nombre, ajusta la URL.

---

## 4. Reiniciar el backend tras cambios

Después de cambiar variables o ejecutar scripts:

```powershell
az webapp restart --name api-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app
```

---

## 5. Ver logs del backend

**Si az CLI falla (ej. purview):** Usa el script con Az PowerShell:
```powershell
.\scripts\view-backend-logs.ps1 -OpenPortal
```

**Manual:** Azure Portal → **api-customerchatbotasmzl** → **Monitoring** → **Log stream** (logs en vivo). O **Application Insights** si está configurado.

**Errores típicos:** "Error al enviar" suele ser 429 (rate limit) o 500 (fallo del agente). Revisa en Log stream si aparece "Rate limit", "429", "Error running AI agent" o excepciones de conexión.

---

## 5a. "Error al enviar" – diagnóstico paso a paso

**Síntoma:** Al enviar un mensaje en el chat aparece "Error al enviar. Si el servicio está ocupado, usa «Registrar cotización» para guardar tus datos."

**Paso 1 – Ver el error real en el navegador**
1. Abre la app: `https://app-customerchatbotasmzl.azurewebsites.net`
2. Abre DevTools (F12) → pestaña **Network**
3. Envía un mensaje en el chat
4. Busca la petición `message` (POST a `/api/chat/message`)
5. Haz clic en ella y revisa:
   - **Status:** 429 = rate limit, 500 = error del servidor, 404 = endpoint no existe, 0/CORS = frontend no llega al backend
   - **Response:** cuerpo del error (a veces incluye `detail` con el mensaje real)

**Paso 2 – Revisar Log stream del backend**
1. Azure Portal → **api-customerchatbotasmzl** → **Monitoring** → **Log stream**
2. Envía otro mensaje en el chat
3. Busca líneas con "ERROR", "429", "Rate limit", "Error running AI agent" o excepciones de Python

**Causas frecuentes y soluciones**

| Causa | Solución |
|-------|----------|
| **429 (rate limit)** | Espera 2–3 min. Si persiste, solicita más cuota en Azure OpenAI o usa DSPM-AI-Project (250K TPM). |
| **500 (error interno)** | Revisa Log stream para ver el traceback. Suele ser agente mal configurado, variable faltante o fallo de conexión a Foundry/Search. |
| **CORS / 0** | Ejecuta `.\scripts\fix-cors.ps1` o en **api-** → Configuration → `ALLOWED_ORIGINS_STR` añade `https://app-customerchatbotasmzl.azurewebsites.net`. |
| **404** | El frontend no está llamando al backend correcto. En **app-** → Configuration → `VITE_API_BASE_URL` = `https://api-customerchatbotasmzl.azurewebsites.net`. |
| **Timeout (60 s)** | El agente tarda demasiado. Revisa latencia en Log stream; si hay cold start, el primer mensaje puede tardar más. |

**Reiniciar backend (sin az CLI):**
```powershell
.\scripts\update-app-container.ps1 -RestartOnly -BackendOnly
```

**"Application Error" (backend no responde):** El contenedor puede estar fallando al arrancar. Revertir a la imagen anterior:
```powershell
.\scripts\update-app-container.ps1 -ImageTag "opti-summit" -BackendOnly
```

---

## 6. "Application Error" en el frontend

Si ves ": ( Application Error" en `app-customerchatbotasmzl`:

1. **Credenciales ACR:** El webapp debe poder hacer pull del registro. Si faltan credenciales:
   ```powershell
   # Habilitar admin en ACR (si no está)
   az acr update -n optisummitacr --resource-group rg-summit-dspm-ai-resources-app --admin-enabled true

   # Obtener usuario y contraseña
   az acr credential show -n optisummitacr -g rg-summit-dspm-ai-resources-app -o table

   # Configurar webapp (reemplaza USER y PASS con los valores anteriores)
   az webapp config container set --name app-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app `
     --docker-custom-image-name optisummitacr.azurecr.io/frontend:opti-summit `
     --docker-registry-server-url https://optisummitacr.azurecr.io `
     --docker-registry-server-user <USER> `
     --docker-registry-server-password <PASS>

   az webapp restart --name app-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app
   ```
2. **Log stream:** Azure Portal → **app-customerchatbotasmzl** → **Monitoring** → **Log stream** para ver si el contenedor arranca.
3. **Reconstruir y desplegar:**
   ```powershell
   .\scripts\build-and-push.ps1 -AcrName optisummitacr -ImageTag opti-summit
   az webapp restart --name app-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app
   ```
4. **Variables:** Comprueba que `VITE_API_BASE_URL` esté en **app-customerchatbotasmzl** → **Configuration** → **Application settings** (ej. `https://api-customerchatbotasmzl.azurewebsites.net`).

---

## 7. Oportunidades de cotización: ¿dónde se guardan los datos?

Los datos de cotización (nombre, correo, teléfono, empresa, servicio) se guardan en el **backend**:

- **Ubicación por defecto:** archivo JSONL en `/tmp/opportunities.jsonl` (en el contenedor del API).
- **Variable opcional:** `OPPORTUNITIES_DATA_DIR` para cambiar el directorio (ej. `/home/LogFiles/opportunities`).
- **Vista:** El panel **Opportunities** en el dashboard muestra las oportunidades registradas.
- **Flujo:** El agente pide nombre, correo, teléfono, empresa y servicio. Si el chat falla (ej. error 429), el usuario puede usar el botón **«Registrar cotización»** en el chat para guardar los datos directamente.

**Error 429 (Too Many Requests):**
- **Causa:** Límite de cuota de Azure OpenAI (TPM = tokens por minuto, RPM = solicitudes por minuto). Es por **suscripción**, no por sesión. Abrir otra sesión o ventana **no ayuda** — comparten la misma cuota.
- **Reintentos:** El backend reintenta hasta 8 veces con espera de 12 segundos entre intentos.
- **¿Aumentar más?** Se puede subir a 10–12 reintentos, pero el beneficio es limitado. La solución real es solicitar más cuota en Azure Portal.
- **Cómo aumentar cuota:** (1) **Capacidad del deployment:** `azd env set AZURE_ENV_MODEL_CAPACITY 100` y luego `azd provision` para reservar más capacidad. (2) **Cuota de suscripción:** Azure Portal → Azure OpenAI → Usage + quotas → Request quota increase → región, modelo, TPM deseado.
- **Mensaje al usuario:** Mientras espera, ve «Procesando... Si tarda más de lo habitual, el servicio puede estar ocupado. Por favor espera.» Si tras los reintentos falla, el mensaje indica esperar 2-3 minutos e invita a usar «Registrar cotización».
- **Botón «Registrar cotización»:** Si el 429 persiste, el usuario puede guardar sus datos sin depender del agente de IA.

---

---

## 8. Dashboard no muestra datos (eventos de seguridad, oportunidades)

**Síntomas:** El dashboard muestra 0 en "Solicitudes bloqueadas", "Prompt injection" y "Oportunidades registradas" aunque bloqueaste un prompt o registraste datos en el chat.

**Causas posibles:**

1. **API base URL incorrecta:** El frontend debe llamar al backend. En **app-** (frontend) → Configuration → verifica `VITE_API_BASE_URL` = `https://api-{suffix}.azurewebsites.net` (la URL del backend).
2. **CORS:** El backend debe permitir el origen del frontend. En **api-** → Configuration → `ALLOWED_ORIGINS_STR` debe incluir `https://app-{suffix}.azurewebsites.net`.
3. **Persistencia de datos:** Los eventos y oportunidades se guardan en JSONL. En App Service, el deployment usa `SECURITY_EVENTS_DATA_DIR` y `OPPORTUNITIES_DATA_DIR` apuntando a `/home/LogFiles/data/`. Si faltan, añade en **api-** → Configuration:
   - `SECURITY_EVENTS_DATA_DIR` = `/home/LogFiles/data/security-events`
   - `OPPORTUNITIES_DATA_DIR` = `/home/LogFiles/data/opportunities`
4. **Verificar API:** Abre `https://api-{suffix}.azurewebsites.net/api/security/events?limit=10` en el navegador. Si devuelve `[]`, no hay eventos guardados. Si devuelve datos, el problema es CORS o la URL del frontend.

**Acción:** Tras añadir variables, reinicia el backend: `az webapp restart --name api-{suffix} --resource-group {rg}`.

---

## 9. Oportunidades no se registran desde el chat

**Síntomas:** El usuario comparte nombre, correo, teléfono y empresa en el chat, pero la oportunidad no aparece en el panel Opportunities.

**Diagnóstico rápido:** Ejecuta el script de roles y permisos:
```powershell
.\scripts\diagnose-roles-and-permissions.ps1
```

**Solución implementada (fallback):** El backend extrae automáticamente los datos de contacto del mensaje y registra la oportunidad. Formatos soportados:
- `Nombre, email@x.com, teléfono, Empresa` (ej: `Diana Fernández, dfernandez@opti.com.mx, 5519387611, OPTI`)

**Si sigue fallando:**

1. **Verificar despliegue:** Los cambios requieren reconstruir y desplegar el backend:
   ```powershell
   .\scripts\build-and-push.ps1 -AcrName optisummitacr -ImageTag opti-summit
   az webapp restart --name api-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app
   ```
2. **Verificar OPPORTUNITIES_DATA_DIR:** En api- → Configuration → debe estar `OPPORTUNITIES_DATA_DIR=/home/LogFiles/data/opportunities`
3. **Logs:** Revisar Application Insights o Log stream del backend para buscar "Oportunidad registrada desde fallback" o "Error appending opportunity"
4. **Solución temporal:** Usa el botón **«Registrar cotización»** en el chat para guardar los datos directamente.

---

## 10. Usar proyecto DSPM-AI-Project (East US, 250K TPM)

Para aprovechar la cuota de 250K TPM en DSPM-AI-Project:

### Paso 1 – Obtener Resource ID

En Azure Portal → Azure AI Foundry → tu workspace → Projects → **dspm-ai-project** → Properties → copiar **Resource ID**.

Formato: `/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{account}/projects/dspm-ai-project`

### Paso 2 – Configurar y desplegar

```powershell
cd "D:\02. Demos\02.Microsoft_Summit_2026\customer-chatbot-solution-accelerator"

az login
az account set --subscription "e52da50f-bfae-4cbf-9188-68d2e5833dd4"
azd auth login

# Usar tu proyecto existente (reemplaza con tu Resource ID real)
azd env set AZURE_EXISTING_AI_PROJECT_RESOURCE_ID "/subscriptions/e52da50f-bfae-4cbf-9188-68d2e5833dd4/resourceGroups/{tu-rg}/providers/Microsoft.CognitiveServices/accounts/{tu-cuenta}/projects/dspm-ai-project"

azd up
```

Esto crea: AI Search, Cosmos DB, API, frontend. La conexión a AI Search se crea en el proyecto existente.

### Paso 3 – Subir datos (productos, políticas)

```powershell
.\infra\scripts\data_scripts\run_upload_data_scripts.ps1 -resource_group "rg-summit-dspm-ai-resources-app"
```

### Paso 4 – Crear agentes en DSPM-AI-Project

```powershell
.\infra\scripts\agent_scripts\run_create_agents_scripts.ps1 -resourceGroup "rg-summit-dspm-ai-resources-app"
```

El script crea los agentes en el proyecto configurado y actualiza `FOUNDRY_CHAT_AGENT`, `FOUNDRY_PRODUCT_AGENT`, `FOUNDRY_POLICY_AGENT` en el App Service.

### Paso 5 – Reiniciar backend

```powershell
az webapp restart --name api-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app
```

**Nota:** El endpoint de AI Foundry es `https://{nombre-cuenta}.services.ai.azure.com/api/projects/{nombre-proyecto}`. El nombre de la cuenta es el recurso Cognitive Services, no el nombre del proyecto.

---

## Resumen rápido

1. Revisar variables del **backend** (api-), no solo del frontend.
2. Ejecutar `run_upload_data_scripts.ps1`.
3. Ejecutar `run_create_agents_scripts.ps1`.
4. Reiniciar el backend.
5. Probar el chat de nuevo.
