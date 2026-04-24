from __future__ import annotations

from dataclasses import dataclass

from profiler_agent.models import ScenarioDefinition


@dataclass(slots=True)
class HuggingFacePromptBuilder:
    def scenario_system_prompt(self) -> str:
        return (
            "Sos un entrevistador calido, empatico y muy coloquial de Argentina. "
            "Reescribis situaciones cotidianas como preguntas breves, naturales y cercanas, sin sonar robotico. "
            "Mantenes voseo rioplatense, no repetis muletillas, no agregas opciones nuevas y no cambias el sentido del escenario. "
            "Devolves solo JSON valido."
        )

    def scenario_user_prompt(self, scenario: ScenarioDefinition, recent_prompts: list[str] | None = None) -> str:
        options = "\n".join(
            f"{index + 1}. {option['text']}" for index, option in enumerate(scenario["options"])
        )
        recent_prompt_block = ""
        if recent_prompts:
            formatted_history = "\n".join(f"- {prompt}" for prompt in recent_prompts)
            recent_prompt_block = (
                "Estas fueron algunas formulaciones recientes. No repitas el arranque, el ritmo ni las muletillas:\n"
                f"{formatted_history}\n\n"
            )
        return (
            "Quiero que reformules esta situacion como una pregunta para una entrevista breve de perfil de aprendizaje. "
            "Usa palabras como IMAGINATE que, SUPONENTE que, SI TE PASARA que, etc. para sonar mas natural y cercana. "
            "NO ABUSES DE UNA MISMA ENTRADA, VARIA EL ARRANQUE, EL RITMO Y LAS MULETILLAS PARA QUE NO SUENE A PREGUNTA DE ROBOT. "
            "Tiene que sonar humana, cercana y variar la entrada respecto de otras preguntas. "
            "Debe mencionar la situacion, invitar a elegir una opcion y quedar en un maximo de dos oraciones.\n\n"
            "NO INCLUYAS LAS OPCIONES DISPONIBLES en el planteo de la pregunta, formula las opciones UNA SÓLA VEZ como parte de la respuesta que va a elegir el alumno. "
            f"{recent_prompt_block}"
            f"Situacion original: {scenario['situation']}\n"
            f"Opciones disponibles:\n{options}\n\n"
            'Devolve JSON exacto con este formato: {"prompt": "..."}'
        )

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