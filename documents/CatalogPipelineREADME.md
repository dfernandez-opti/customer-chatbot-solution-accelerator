# Canalizacion RAG - Servicios OPTI 2026

Pipeline para convertir el contenido de "Servicios OPTI 2026 - Presentacion comercial" en datos estructurados RAG-ready y cargarlos a Cosmos DB y opcionalmente a Azure AI Search.

## Estructura

```
data/
  servicios_opti_2026_seed.json    # Seed con 17 servicios (A-Q)
scripts/
  ingest_cosmos.py                 # Ingesta a Cosmos DB
  ingest_search.py                 # Ingesta a Azure AI Search (opcional)
  retrieval_smoke.py               # Pruebas de recuperacion
src/catalog/
  schema.py                        # Modelos y validacion
  normalize.py                     # Helpers: slug, content_for_embedding
tests/
  test_retrieval_smoke.py         # Pytest para recuperacion
```

## Requisitos

- Python 3.11+
- Dependencias: `azure-cosmos`, `azure-identity`, `azure-search-documents`, `openai`, `pydantic`, `python-dotenv`

## Donde configurar (una sola vez)

Crea un archivo `.env` en **una** de estas ubicaciones:

| Ubicacion | Quien lo usa |
|-----------|--------------|
| `customer-chatbot-solution-accelerator/.env` (raiz) | Scripts de ingesta |
| `customer-chatbot-solution-accelerator/src/api/.env` | API + scripts de ingesta |

Si ya tienes `.env` en `src/api/` para la API, los scripts tambien lo leen. No necesitas duplicar.

Copia `.env.example` a `.env` y completa los valores:

```bash
cp .env.example .env
```

## Variables de entorno

### Cosmos DB (ingest_cosmos.py)

| Variable | Descripcion |
|----------|-------------|
| COSMOS_ENDPOINT o AZURE_COSMOSDB_ENDPOINT | URL completa (https://...) |
| AZURE_COSMOSDB_ACCOUNT | Nombre de cuenta (alternativa) |
| COSMOS_DATABASE | Base de datos (default: ecommerce_db) |
| COSMOS_SERVICIOS_CONTAINER | Contenedor (default: servicios) |

### Azure AI Search (ingest_search.py)

| Variable | Descripcion |
|----------|-------------|
| SEARCH_ENDPOINT o AZURE_SEARCH_ENDPOINT | URL del servicio Search |
| AOAI_ENDPOINT o AZURE_OPENAI_ENDPOINT | URL de Azure OpenAI |
| AOAI_EMBEDDING_DEPLOYMENT | Nombre del deployment de embeddings |
| SEARCH_INDEX | Nombre del indice (default: servicios_index) |

## Ejecucion local

### 1. Ingesta a Cosmos DB

```bash
# Desde la raiz del proyecto
python scripts/ingest_cosmos.py --seed data/servicios_opti_2026_seed.json
```

Validar sin escribir:

```bash
python scripts/ingest_cosmos.py --dry-run
```

### 2. Ingesta a Azure AI Search (opcional)

```bash
python scripts/ingest_search.py --seed data/servicios_opti_2026_seed.json
```

### 3. Pruebas de recuperacion

Sin Azure Search (keyword match sobre el seed):

```bash
python scripts/retrieval_smoke.py
```

Con Azure Search configurado (SEARCH_ENDPOINT en .env):

```bash
python scripts/retrieval_smoke.py
```

Pytest:

```bash
pytest tests/test_retrieval_smoke.py -v
```

## Criterio de aceptacion

- `python scripts/ingest_cosmos.py --seed data/servicios_opti_2026_seed.json` ejecuta sin errores
- En Cosmos DB se ven documentos por servicio con campos completos
- Al menos 10 de las queries de prueba encuentran el servicio correcto en top-3

## Integracion con el agente

Para que el agente de catalogo use estos datos:

1. Actualizar el plugin de productos o crear un plugin de servicios que consulte el contenedor `servicios` en Cosmos DB o el indice `servicios_index` en Azure AI Search.
2. Configurar el agente con las instrucciones para buscar en el nuevo esquema (categoria, nombre, descripcion, problemas_que_resuelve, incluye, beneficios, keywords, faq_examples).

## Modelo de datos (Cosmos DB)

Contenedor: `servicios`  
Particion: `/categoria`

```json
{
  "id": "servicio_<slug>_<hash>",
  "categoria": "Seguridad | ITSM | Cloud & Data | ...",
  "nombre": "string",
  "descripcion": "string",
  "problemas_que_resuelve": ["..."],
  "incluye": ["..."],
  "beneficios": ["..."],
  "tecnologias": ["..."],
  "keywords": ["..."],
  "faq_examples": ["..."],
  "source": {"document": "...", "pages": [1,2,3]},
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601",
  "version": "2026.1"
}
```
