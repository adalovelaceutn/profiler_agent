from __future__ import annotations

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
async def test_a2a_returns_existing_profile_from_mcp() -> None:
    task = await _send_user_message("id_alumno: copilot-consistency-smoke-20260418")

    response_text = _extract_task_text(task)

    assert task.status.state == "completed"
    assert "Encontre el perfil Kolb del alumno copilot-consistency-smoke-20260418" in response_text
    assert "Estilo: activo." in response_text
    assert "AE=0.4, RO=0.1, AC=0.3, CE=0.2" in response_text


@pytest.mark.asyncio
async def test_a2a_starts_interview_for_nonexistent_student() -> None:
    student_id = f"pytest-a2a-missing-{uuid.uuid4().hex}"
    task = await _send_user_message(f"id_alumno: {student_id}")

    response_text = _extract_task_text(task)

    assert task.status.state == "input-required"
    assert "Arranquemos tranqui" in response_text
    assert "conocerte mejor" in response_text
    assert "Te compras un electrodomestico complejo y nuevo que nunca usaste" in response_text
    assert "1." in response_text
    assert "2." in response_text
    assert "3." in response_text