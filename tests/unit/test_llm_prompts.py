from __future__ import annotations

from profiler_agent.assessment_data import ASSESSMENTS
from profiler_agent.llm.prompts import HuggingFacePromptBuilder


def test_llm_prompt_builder_returns_strict_system_prompt() -> None:
    builder = HuggingFacePromptBuilder()

    prompt = builder.parser_system_prompt()

    assert "clasificador estricto" in prompt
    assert "JSON valido" in prompt
    assert "rioplatense" in prompt


def test_llm_prompt_builder_includes_scenario_options_and_json_contract() -> None:
    builder = HuggingFacePromptBuilder()
    scenario = ASSESSMENTS[0]["scenarios"][0]

    prompt = builder.parser_user_prompt("Me mando de una", scenario)

    assert "Situacion:" in prompt
    assert scenario["situation"] in prompt
    assert "Opciones:" in prompt
    assert scenario["options"][0]["text"] in prompt
    assert "Respuesta del alumno: Me mando de una" in prompt
    assert '"selected_option_index"' in prompt