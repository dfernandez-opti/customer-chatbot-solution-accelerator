# Checklist de despliegue - Fix "cannot unpack non-iterable bool object"

## 1. Verificar que el fix está en el código
- `src/api/app/routers/chat.py` línea ~153: debe ser `return False, False` (no `return False`)

## 2. Reconstruir y subir la imagen del backend
```powershell
cd "d:\02. Demos\02.Microsoft_Summit_2026\customer-chatbot-solution-accelerator"
.\scripts\build-and-push.ps1 -AcrName optisummitacr -ImageTag opti-summit
```
Espera a que termine sin errores.

## 3. Forzar que App Service use la nueva imagen
Con el mismo tag, App Service puede no hacer pull automático. Usa uno de estos:

**Opción A – Restart (prueba primero):**
```powershell
az webapp restart --name api-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app
```

**Opción B – Si sigue el error, usar un tag nuevo para forzar pull:**
```powershell
# Reconstruir con tag nuevo (ej: opti-summit-v2)
.\scripts\build-and-push.ps1 -AcrName optisummitacr -ImageTag opti-summit-v2

# Actualizar App Service para usar el nuevo tag
az webapp config container set --name api-customerchatbotasmzl --resource-group rg-summit-dspm-ai-resources-app --docker-custom-image-name optisummitacr.azurecr.io/backend:opti-summit-v2
```

## 4. Esperar 1-2 minutos
El reinicio puede tardar. Prueba de nuevo el chat.

## 5. Si sigue fallando
- Azure Portal → api-customerchatbotasmzl → Deployment Center → verifica que use la imagen correcta
- Log stream: revisa si hay errores al procesar mensajes
