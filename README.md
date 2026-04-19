# profiler_agent

Agente en Python con LangGraph que expone una interfaz A2A, recibe un registro de alumno y construye su perfil Kolb mediante una entrevista guiada por escenarios. El resultado final se persiste en un servidor MCP.

## Flujo

1. Llega un mensaje A2A con un JSON que incluye `id`, `nombre` y `apellido`.
2. El agente saluda, explica brevemente la dinamica y dispara un grafo LangGraph con loop de entrevista.
3. El loop usa selección incremental de escenarios, parser de respuesta, scoring en tiempo real y early exit por confianza.
4. Al cerrar, guarda el perfil generado en MCP.

## Estructura

- `src/profiler_agent/server.py`: arranque FastAPI + A2A.
- `src/profiler_agent/a2a/executor.py`: contrato `AgentExecutor` del SDK A2A.
- `src/profiler_agent/interview/engine.py`: grafo LangGraph y lógica de entrevista.
- `src/profiler_agent/interview/prompts.py`: prompts conversacionales de la entrevista en tono rioplatense.
- `src/profiler_agent/mcp/client.py`: cliente MCP por stdio, SSE o streamable HTTP.
- `src/profiler_agent/llm/huggingface.py`: capa LLM configurable con modelos de Hugging Face.
- `src/profiler_agent/llm/prompts.py`: prompts del parser LLM y contrato de salida JSON.

## Diagramas

En [doc/engine_class_diagram.puml](doc/engine_class_diagram.puml) está el diagrama de clases y helpers de `engine.py`.
En [doc/engine_sequence_diagram.puml](doc/engine_sequence_diagram.puml) está el flujo de secuencia completo entre A2A, engine, MCP y Hugging Face.

Para abrirlos en VS Code, alcanza con abrir el archivo `.puml`. Si tienes una extensión PlantUML instalada, podrás previsualizarlos directamente.

## Preparación

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .[test]
cp .env.example .env
```

Completa `.env` con:

- `HF_API_KEY`: credencial para Hugging Face.
- `HF_MODEL`: modelo a usar en la capa LLM.
- `MCP_TRANSPORT`: `stdio`, `sse` o `streamable-http`.
- `MCP_SERVER_URL`: URL del servidor MCP remoto cuando no uses `stdio`.
- `MCP_SERVER_COMMAND` y `MCP_SERVER_ARGS`: comando del servidor MCP local si usas `stdio`.
- `MCP_GET_PROFILE_TOOL` y `MCP_SAVE_PROFILE_TOOL`: tools del servidor MCP.

Configuracion remota ya preparada para este workspace:

- `MCP_TRANSPORT=sse`
- `MCP_SERVER_URL=https://ominous-funicular-v6xq97xww67w2w466-8000.app.github.dev/sse`
- `MCP_GET_PROFILE_TOOL=obtener_perfil_kolb`
- `MCP_SAVE_PROFILE_TOOL=actualizar_perfil_kolb`

## Ejecución

```bash
. .venv/bin/activate
uvicorn profiler_agent.server:app --host 0.0.0.0 --port 8000
```

## Despliegue

El repositorio ya ignora `.env` y `.venv` en `.gitignore`, así que no hace falta tocar secretos ni artefactos locales para publicarlo.

Se agregó [requirements.txt](requirements.txt) para plataformas que no instalan desde `pyproject.toml`.

Como el proyecto usa layout `src/`, ese archivo también instala el paquete local para que `profiler_agent` quede importable en producción.

Comandos sugeridos:

```bash
pip install -r requirements.txt
```

```bash
uvicorn profiler_agent.server:app --host 0.0.0.0 --port ${PORT:-8000}
```

La app ahora acepta tanto `APP_PORT` como `PORT`, que es la variable estándar en varios proveedores de despliegue.

Endpoints relevantes:

- `GET /.well-known/agent-card.json`
- `GET /.well-known/agent.json`
- `POST /`
- `GET /healthz`

## Ejemplo de inicio de entrevista

Envia al endpoint A2A un mensaje de texto con este formato JSON:

- `{"id":"12345","nombre":"Ada","apellido":"Lovelace"}`

Luego el agente responderá una situación por vez. Para responder, el alumno puede mandar `1`, `2`, `3` o texto libre parecido a alguna opción.

## Tests

Para correr el test de integración contra el MCP remoto configurado en `.env`:

```bash
. .venv/bin/activate
pytest -m integration
```

El test usa ids únicos por ejecución para evitar colisiones y valida dos cosas:

- un alumno inexistente devuelve `None`
- guardar y recuperar un perfil produce un roundtrip consistente

También hay tests A2A de punta a punta sobre la app local:

- un registro de alumno valido entra en estado `input-required` e inicia la entrevista guiada
- un payload invalido devuelve una instruccion clara para reenviar el JSON esperado

Y tests unitarios para fijar el tono y los prompts:

- prompts conversacionales de entrevista
- prompts del parser LLM para Hugging Face