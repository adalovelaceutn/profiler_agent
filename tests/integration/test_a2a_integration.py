from __future__ import annotations

import json
import uuid

import httpx
import pytest
from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import Message, MessageSendParams, Role, Task, TextPart

from profiler_agent.server import create_app


pytestmark = pytest.mark.integration


def _extract_task_text(task: Task) -> str:
    status_message = task.status.message
    assert status_message is not None
    parts = status_message.parts or []
    text_parts: list[str] = []
    for part in parts:
        payload = part.model_dump(mode="json", by_alias=True)
        text = payload.get("text")
        if isinstance(text, str) and text:
            text_parts.append(text)
    return "\n".join(text_parts)


async def _send_user_message(text: str) -> Task:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as http_client:
        client = JsonRpcTransport(httpx_client=http_client, url="http://testserver/")
        result = await client.send_message(
            MessageSendParams(
                message=Message(
                    messageId=f"msg-{uuid.uuid4().hex}",
                    role=Role.user,
                    parts=[TextPart(text=text)],
                )
            )
        )
    assert isinstance(result, Task)
    return result


@pytest.mark.asyncio
async def test_a2a_starts_interview_from_student_record_payload() -> None:
    task = await _send_user_message(
        json.dumps(
            {
                "id": "copilot-consistency-smoke-20260418",
                "nombre": "Ada",
                "apellido": "Lovelace",
            }
        )
    )

    response_text = _extract_task_text(task)

    assert task.status.state == "input-required"
    assert "Hola Ada Lovelace, mucho gusto." in response_text
    assert "Voy a hacerte unas preguntas cortitas" in response_text
    assert "perfil Kolb" in response_text
    assert "Te compras un electrodomestico complejo y nuevo que nunca usaste" in response_text


@pytest.mark.asyncio
async def test_a2a_rejects_invalid_student_record_payload() -> None:
    task = await _send_user_message(json.dumps({"id": f"pytest-a2a-missing-{uuid.uuid4().hex}", "nombre": "Ada"}))

    response_text = _extract_task_text(task)

    assert task.status.state == "input-required"
    assert "registro de alumno valido en JSON" in response_text