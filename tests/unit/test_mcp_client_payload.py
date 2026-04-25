from __future__ import annotations

from profiler_agent.config import Settings
from profiler_agent.mcp.client import KolbMCPClient
from profiler_agent.models import KolbProfile, KolbVector


def test_to_remote_payload_maps_to_exact_mcp_schema() -> None:
    client = KolbMCPClient(settings=Settings())
    profile = KolbProfile(
        student_id=123,
        current_vector=KolbVector(AE=0.42, RO=0.31, AC=0.72, CE=0.55),
        style="Converging",
        confidence=0.89,
        answered_scenarios=[1, 2, 3, 4, 5, 6, 7, 8, 9],
        answers=[{"scenario_id": 1, "dimension": "AC", "answer": "..."}],
        source="generated_via_guided_interview",
        summary="...",
    )

    payload = client._to_remote_payload(profile)

    assert payload["status"] == "completed"
    assert payload["student_id"] == 123
    assert payload["source"] == "generated_via_guided_interview"
    assert payload["summary"] == "..."

    kolb_profile = payload["kolb_profile"]
    assert kolb_profile["student_id"] == 123
    assert kolb_profile["assessment_name"] == "Lovelace Everyday Life Profiling"
    assert kolb_profile["model_name"] == "Kolb Cycle"
    assert kolb_profile["current_vector"] == {"AE": 0.42, "RO": 0.31, "AC": 0.72, "CE": 0.55}
    assert kolb_profile["style"] == "Converging"
    assert kolb_profile["confidence"] == 0.89
    assert kolb_profile["assessment_answers"] == [{"scenario_id": 1, "dimension": "AC", "answer_text": "..."}]
    assert kolb_profile["scenarios_completed"] == [1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_to_local_profile_supports_new_envelope_format() -> None:
    client = KolbMCPClient(settings=Settings())
    remote_data = {
        "kolb_profile": {
            "student_id": 123,
            "assessment_name": "Lovelace Everyday Life Profiling",
            "model_name": "Kolb Cycle",
            "current_vector": {"AE": 0.42, "RO": 0.31, "AC": 0.72, "CE": 0.55},
            "style": "Converging",
            "confidence": 0.89,
            "assessment_answers": [{"scenario_id": 1, "dimension": "AC", "answer_text": "..."}],
            "scenarios_completed": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        },
        "source": "generated_via_guided_interview",
        "summary": "...",
    }

    profile = client._to_local_profile(student_id=123, data=remote_data)

    assert profile.student_id == 123
    assert profile.style == "Converging"
    assert profile.confidence == 0.89
    assert profile.current_vector.model_dump() == {"AE": 0.42, "RO": 0.31, "AC": 0.72, "CE": 0.55}
    assert profile.answered_scenarios == [1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_to_local_profile_supports_sql_schema_format() -> None:
    client = KolbMCPClient(settings=Settings())
    remote_data = {
        "student_id": 123,
        "assessment_name": "Lovelace Everyday Life Profiling",
        "model_name": "Kolb Cycle",
        "status": "completed",
        "style": "Converging",
        "confidence": 0.89,
        "ae_score": 0.42,
        "ro_score": 0.31,
        "ac_score": 0.72,
        "ce_score": 0.55,
        "source": "generated_via_guided_interview",
        "summary": "...",
        "answers": [{"scenario_id": 1, "dimension": "AC", "answer_text": "texto respuesta"}],
        "answered_scenarios": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    }

    profile = client._to_local_profile(student_id=123, data=remote_data)

    assert profile.student_id == 123
    assert profile.style == "Converging"
    assert profile.confidence == 0.89
    assert profile.current_vector.model_dump() == {"AE": 0.42, "RO": 0.31, "AC": 0.72, "CE": 0.55}
    assert profile.answered_scenarios == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert profile.answers == [{"scenario_id": 1, "dimension": "AC", "answer": "texto respuesta"}]


def test_to_local_profile_supports_legacy_format() -> None:
    client = KolbMCPClient(settings=Settings())
    remote_data = {
        "preferencia_principal": "activo",
        "evidencia": [{"texto": "Le gusta experimentar"}],
        "kolb_profile": {
            "activo": 0.4,
            "reflexivo": 0.1,
            "teorico": 0.3,
            "pragmatico": 0.2,
        },
    }

    profile = client._to_local_profile(student_id=777, data=remote_data)

    assert profile.student_id == 777
    assert profile.style == "activo"
    assert profile.confidence is None
    assert profile.current_vector.model_dump() == {"AE": 0.4, "RO": 0.1, "AC": 0.3, "CE": 0.2}
    assert profile.summary == "Le gusta experimentar"


def test_to_legacy_remote_payload_maps_scores() -> None:
    client = KolbMCPClient(settings=Settings())
    profile = KolbProfile(
        student_id=35,
        current_vector=KolbVector(AE=0.42, RO=0.31, AC=0.72, CE=0.55),
        style="Converging",
        confidence=0.89,
        answered_scenarios=[1, 2],
        answers=[],
        source="integration_test_mock",
        summary="Mock Kolb profile guardado para id_alumno 35",
    )

    payload = client._to_remote_payload(profile)

    assert payload["student_id"] == 35
    assert payload["kolb_profile"]["current_vector"] == {"AE": 0.42, "RO": 0.31, "AC": 0.72, "CE": 0.55}


def test_sql_payload_roundtrip_is_exact() -> None:
    client = KolbMCPClient(settings=Settings())
    original = KolbProfile(
        student_id=35,
        assessment_name="Lovelace Everyday Life Profiling",
        model_name="Kolb Cycle",
        current_vector=KolbVector(AE=0.42, RO=0.31, AC=0.72, CE=0.55),
        style="Converging",
        confidence=0.89,
        answered_scenarios=[1, 2, 3, 4, 5, 6, 7, 8, 9],
        answers=[{"scenario_id": 1, "dimension": "AC", "answer": "..."}],
        source="generated_via_guided_interview",
        summary="...",
    )

    persisted_payload = client._to_remote_payload(original)
    recovered_profile = client._to_local_profile(student_id=35, data=persisted_payload)
    recovered_payload = client._to_remote_payload(recovered_profile)

    assert recovered_payload == persisted_payload
