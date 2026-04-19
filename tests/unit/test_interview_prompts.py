from __future__ import annotations

from profiler_agent.assessment_data import ASSESSMENTS
from profiler_agent.interview.prompts import InterviewPrompts
from profiler_agent.models import KolbProfile, KolbVector


def test_interview_prompt_uses_empatic_rioplatense_tone() -> None:
    prompts = InterviewPrompts()
    scenario = ASSESSMENTS[0]["scenarios"][0]

    prompt = prompts.build_scenario_prompt(
        scenario=scenario,
        chunk="A",
        answered_count=0,
        student_name="Ada",
        student_last_name="Lovelace",
    )
    rendered = prompts.render_prompt(prompt)

    assert "Hola Ada Lovelace, mucho gusto." in rendered
    assert "Voy a hacerte unas preguntas cortitas" in rendered
    assert "acompanarte" in rendered
    assert "perfil Kolb" in rendered
    assert "Te compras un electrodomestico complejo y nuevo que nunca usaste." in rendered
    assert "situacion bien cotidiana" in rendered
    assert "te sentis mas identificado" in rendered


def test_interview_prompt_varies_the_intro_between_scenarios() -> None:
    prompts = InterviewPrompts()
    first_scenario = ASSESSMENTS[0]["scenarios"][0]
    second_scenario = ASSESSMENTS[0]["scenarios"][1]

    first_prompt = prompts.build_scenario_prompt(first_scenario, chunk="A", answered_count=0)
    second_prompt = prompts.build_scenario_prompt(second_scenario, chunk="A", answered_count=1)

    assert first_prompt.prompt != second_prompt.prompt
    assert first_scenario["situation"] in first_prompt.prompt
    assert second_scenario["situation"] in second_prompt.prompt


def test_interview_completion_omits_confidence_when_missing() -> None:
    prompts = InterviewPrompts()
    profile = KolbProfile(
        student_id="demo",
        current_vector=KolbVector(AE=4, RO=2, AC=3, CE=1),
        style="activo",
        confidence=None,
        answered_scenarios=[],
        answers=[],
        source="test",
        summary="Resumen de cierre.",
    )

    rendered = prompts.render_completion(profile, answered_count=8)

    assert "Con esto ya tengo una base muy buena para arrancar con vos." in rendered
    assert "Resumen de cierre." in rendered
    assert "Confianza:" not in rendered
