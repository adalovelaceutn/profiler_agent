from __future__ import annotations

from profiler_agent.assessment_data import ASSESSMENTS
from profiler_agent.interview.prompts import InterviewPrompts
from profiler_agent.models import KolbProfile, KolbVector


def test_interview_prompt_uses_empatic_rioplatense_tone() -> None:
    prompts = InterviewPrompts()
    scenario = ASSESSMENTS[0]["scenarios"][0]

    prompt = prompts.build_scenario_prompt(scenario=scenario, chunk="A", answered_count=0)
    rendered = prompts.render_prompt(prompt)

    assert "Arranquemos tranqui" in rendered
    assert "acompanarte" in rendered
    assert "Che, te hago una pregunta cortita" in rendered
    assert "te sentis mas identificado" in rendered


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
