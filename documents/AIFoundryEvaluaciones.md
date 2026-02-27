# Configurar evaluaciones de agentes en Azure AI Foundry

## Error: "Unable to create data source configuration from item schema"

Este error aparece cuando el **item schema** de la evaluación no cumple el formato esperado o no coincide con los datos del dataset.

---

## Solución: usar el schema correcto

Para **evaluación de agentes**, el `data_source_config` debe tener:

1. **`type`**: `"custom"`
2. **`item_schema`**: JSON Schema con los campos de tu dataset
3. **`include_sample_schema`**: `true` (obligatorio cuando el target es un agente)

### Schema mínimo para evaluar agentes

```json
{
  "type": "custom",
  "item_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string"
      }
    },
    "required": ["query"]
  },
  "include_sample_schema": true
}
```

### Dataset (JSONL)

Cada línea debe ser un JSON con los campos definidos en `item_schema`:

```
{"query": "¿Qué es CSP?"}
{"query": "Quiero cotización de Servicios de Inteligencia Artificial"}
{"query": "¿Cuál es la política de devolución?"}
```

---

## Configuración desde el portal (Evaluations)

1. **Build → Evaluations → New evaluation**
2. **Data source**: selecciona "Custom" o sube un archivo JSONL
3. **Item schema**: pega el JSON del schema (ver arriba)
4. **Include sample schema**: activa esta opción si evalúas un agente
5. **Target**: selecciona tu agente (ej. `chat-agent-customerchatbotasmzl`)

### Errores comunes

| Problema | Solución |
|----------|----------|
| Schema sin `required` | Añade `"required": ["query"]` al item_schema |
| Falta `include_sample_schema` | Pon `"include_sample_schema": true` para agentes |
| Campos en dataset no coinciden | Los nombres en el JSONL deben coincidir con `properties` del schema |
| Tipos incorrectos | Usa `"type": "string"` para texto, `"type": "number"` para números |

---

## Configuración desde Python (SDK)

```python
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]  # https://dspm-ai-project.services.ai.azure.com/api/projects/proj-default
credential = DefaultAzureCredential()
project_client = AIProjectClient(endpoint=endpoint, credential=credential)
client = project_client.get_openai_client()

# 1. Subir dataset
dataset = project_client.datasets.upload_file(
    name="agent-test-queries",
    version="1",
    file_path="./test-queries.jsonl",
)

# 2. Crear evaluación con schema correcto
data_source_config = {
    "type": "custom",
    "item_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    "include_sample_schema": True,
}

evaluation = client.evals.create(
    name="Evaluación OPTI",
    data_source_config=data_source_config,
    testing_criteria=[
        {
            "type": "azure_ai_evaluator",
            "name": "Task Adherence",
            "evaluator_name": "builtin.task_adherence",
            "data_mapping": {
                "query": "{{item.query}}",
                "response": "{{sample.output_items}}",
            },
            "initialization_parameters": {"deployment_name": "gpt-4o"},
        },
    ],
)

# 3. Crear run con el agente como target
eval_run = client.evals.runs.create(
    eval_id=evaluation.id,
    name="Run OPTI",
    data_source={
        "type": "azure_ai_target_completions",
        "source": {"type": "file_id", "id": dataset.id},
        "input_messages": {
            "type": "template",
            "template": [
                {
                    "type": "message",
                    "role": "user",
                    "content": {"type": "input_text", "text": "{{item.query}}"},
                }
            ],
        },
        "target": {
            "type": "azure_ai_agent",
            "name": "chat-agent-customerchatbotasmzl",
        },
    },
)
```

---

## Referencias

- [Evaluate your AI agents (preview)](https://learn.microsoft.com/en-us/azure/ai-foundry/observability/how-to/evaluate-agent?view=foundry-classic)
- [Cloud Evaluation SDK](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/cloud-evaluation?view=foundry-classic)
