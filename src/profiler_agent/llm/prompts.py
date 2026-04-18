from __future__ import annotations

from dataclasses import dataclass

from profiler_agent.models import ScenarioDefinition


@dataclass(slots=True)
class HuggingFacePromptBuilder:
    def parser_system_prompt(self) -> str:
        return (
            "Sos un clasificador estricto y cuidadoso. "
            "Analizas respuestas de alumnos en espanol rioplatense y devolves solo JSON valido."
        )

    def parser_user_prompt(self, user_input: str, scenario: ScenarioDefinition) -> str:
        options = "\n".join(
            f"{index}. {option['text']}" for index, option in enumerate(scenario["options"])
        )
        return (
            "Quiero que elijas la opcion del escenario que mejor representa la respuesta del alumno. "
            "Si no hay informacion suficiente o la respuesta es ambigua, devolve selected_option_index null "
            "y needs_clarification true.\n\n"
            f"Situacion: {scenario['situation']}\n"
            f"Opciones:\n{options}\n\n"
            f"Respuesta del alumno: {user_input}\n\n"
            'Devolve JSON exacto con este formato: '
            '{"selected_option_index": 0, "needs_clarification": false, "rationale": "..."}'
        )