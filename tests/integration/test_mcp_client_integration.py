from __future__ import annotations

import uuid

import pytest

from profiler_agent.config import Settings
from profiler_agent.mcp.client import KolbMCPClient
from profiler_agent.models import KolbProfile, KolbVector


pytestmark = pytest.mark.integration


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def client(settings: Settings) -> KolbMCPClient:
    return KolbMCPClient(settings=settings)


@pytest.mark.asyncio
async def test_get_profile_returns_none_for_nonexistent_student(client: KolbMCPClient) -> None:
    student_id = int(uuid.uuid4().fields[0] % 1000000)  # Generar int aleatorio

    profile = await client.get_profile(student_id)

    assert profile is None


@pytest.mark.asyncio
async def test_save_and_get_profile_roundtrip(client: KolbMCPClient) -> None:
    student_id = int(uuid.uuid4().fields[0] % 1000000)  # Generar int aleatorio
    expected_summary = "Integration test profiler_agent -> MCP roundtrip"
    profile = KolbProfile(
        student_id=student_id,
        current_vector=KolbVector(AE=8, RO=2, AC=6, CE=4),
        style="Convergente",
        confidence=0.91,
        answered_scenarios=[1, 4, 9, 12, 2, 3, 7, 10],
        answers=[],
        source="integration_test",
        summary=expected_summary,
    )

    save_result = await client.save_profile(profile)
    if save_result.get("error"):
        pytest.skip(f"MCP backend no disponible para guardar perfil: {save_result['error']}")
    
    fetched = await client.get_profile(student_id)

    assert isinstance(save_result, dict)
    assert fetched is not None
    assert fetched.student_id == student_id
    assert fetched.style == "activo"
    assert fetched.summary == expected_summary
    assert fetched.confidence is None
    assert fetched.current_vector.AE == pytest.approx(0.4)
    assert fetched.current_vector.RO == pytest.approx(0.1)
    assert fetched.current_vector.AC == pytest.approx(0.3)
    assert fetched.current_vector.CE == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_save_mock_kolb_profile_for_student_35(client: KolbMCPClient) -> None:
    student_id = 35
    expected_summary = "Mock Kolb profile guardado para id_alumno 35"
    expected_answer = {
        "scenario_id": 1,
        "dimension": "AC",
        "answer": "Mock answer para validacion en Neon",
    }
    expected_scenarios = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    profile = KolbProfile(
        student_id=student_id,
        current_vector=KolbVector(AE=0.42, RO=0.31, AC=0.72, CE=0.55),
        style="Converging",
        confidence=0.89,
        answered_scenarios=expected_scenarios,
        answers=[expected_answer],
        source="integration_test_mock",
        summary=expected_summary,
    )

    persisted_payload = client._to_remote_payload(profile)
    assert persisted_payload["student_id"] == student_id
    assert persisted_payload["kolb_profile"]["assessment_answers"] == [
        {
            "scenario_id": 1,
            "dimension": "AC",
            "answer_text": "Mock answer para validacion en Neon",
        }
    ]
    assert persisted_payload["kolb_profile"]["scenarios_completed"] == expected_scenarios

    save_result = await client.save_profile(profile)
    if save_result.get("error"):
        pytest.skip(f"MCP backend no disponible para guardar perfil: {save_result['error']}")

    assert isinstance(save_result, dict)
    assert "error" not in save_result


@pytest.mark.asyncio
async def test_save_mock_kolb_profile_for_student_15(client: KolbMCPClient) -> None:
    student_id = 15
    expected_summary = "Mock Kolb profile guardado para id_alumno 15"
    expected_answers = [
        {
            "scenario_id": 2,
            "dimension": "RO",
            "answer": "Primero observo y comparo alternativas antes de decidir.",
        },
        {
            "scenario_id": 6,
            "dimension": "AE",
            "answer": "Prefiero probar una version rapida para aprender haciendo.",
        },
    ]
    expected_scenarios = [2, 6, 8, 9]
    profile = KolbProfile(
        student_id=student_id,
        current_vector=KolbVector(AE=0.51, RO=0.44, AC=0.39, CE=0.28),
        style="Assimilating",
        confidence=0.87,
        answered_scenarios=expected_scenarios,
        answers=expected_answers,
        source="integration_test_mock",
        summary=expected_summary,
    )

    persisted_payload = client._to_remote_payload(profile)
    assert persisted_payload["student_id"] == student_id
    assert persisted_payload["kolb_profile"]["assessment_answers"] == [
        {
            "scenario_id": 2,
            "dimension": "RO",
            "answer_text": "Primero observo y comparo alternativas antes de decidir.",
        },
        {
            "scenario_id": 6,
            "dimension": "AE",
            "answer_text": "Prefiero probar una version rapida para aprender haciendo.",
        },
    ]
    assert persisted_payload["kolb_profile"]["scenarios_completed"] == expected_scenarios

    save_result = await client.save_profile(profile)
    if save_result.get("error"):
        pytest.skip(f"MCP backend no disponible para guardar perfil: {save_result['error']}")

    assert isinstance(save_result, dict)
    assert "error" not in save_result