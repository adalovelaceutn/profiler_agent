from __future__ import annotations

from profiler_agent.assessment_data import ASSESSMENTS
from profiler_agent.llm.prompts import HuggingFacePromptBuilder


def test_llm_prompt_builder_returns_strict_system_prompt() -> None:
    builder = HuggingFacePromptBuilder()

    prompt = builder.parser_system_prompt()

    assert "clasificador estricto" in prompt
    assert "JSON valido" in prompt
    assert "rioplatense" in prompt


def test_llm_prompt_builder_creates_scenario_rewrite_prompt() -> None:
    builder = HuggingFacePromptBuilder()
    scenario = ASSESSMENTS[0]["scenarios"][0]

    prompt = builder.scenario_user_prompt(scenario)

    assert "Situacion original:" in prompt
    assert scenario["situation"] in prompt
    assert "Opciones disponibles:" in prompt
    assert scenario["options"][0]["text"] in prompt
    assert '"prompt"' in prompt


def test_llm_prompt_builder_includes_recent_prompt_history_for_variation() -> None:
    builder = HuggingFacePromptBuilder()
    scenario = ASSESSMENTS[0]["scenarios"][1]

    prompt = builder.scenario_user_prompt(
        scenario,
        recent_prompts=[
            "Vamos con una situacion bien cotidiana. Te compras un electrodomestico complejo y nuevo que nunca usaste.",
            "Te propongo una de esas que pasan seguido. Estas en una reunion social donde no conoces a casi nadie.",
        ],
    )

    assert "formulaciones recientes" in prompt
    assert "No repitas el arranque" in prompt
    assert "electrodomestico complejo" in prompt


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