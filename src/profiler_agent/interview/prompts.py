from __future__ import annotations

from dataclasses import dataclass

from profiler_agent.models import KolbProfile, ScenarioDefinition, ScenarioPrompt


CHUNK_TRANSITIONS: dict[str, str] = {
    "A": "Bien ahi, gracias por responder. Ya me voy haciendo una idea de como soles encarar lo nuevo. Sigamos un poquito mas.",
    "B": "Me sirve mucho lo que me venis contando. Con estas ultimas te termino de perfilar mejor.",
}


@dataclass(slots=True)
class InterviewPrompts:
    def build_scenario_prompt(
        self,
        scenario: ScenarioDefinition,
        chunk: str,
        answered_count: int,
        student_name: str | None = None,
        student_last_name: str | None = None,
        transition: str | None = None,
    ) -> ScenarioPrompt:
        return ScenarioPrompt(
            scenario_id=scenario["id"],
            chunk=chunk,
            intro=transition or self._chunk_intro(chunk, answered_count, student_name, student_last_name),
            prompt=self._friendly_prompt(scenario),
            options=[option["text"] for option in scenario["options"]],
            dimension=scenario["dimension"],
        )

    def clarification_feedback(self) -> str:
        return (
            "No termine de ubicar bien tu respuesta en una opcion. Si queres, responde con 1, 2 o 3, "
            "o decimelo de nuevo con otras palabras y lo vemos juntos."
        )

    def render_prompt(self, prompt: ScenarioPrompt, prefix: str | None = None) -> str:
        pieces: list[str] = [
            piece for piece in [prefix, prompt.intro, prompt.prompt] if isinstance(piece, str) and piece
        ]
        options = "\n".join(f"{index + 1}. {option}" for index, option in enumerate(prompt.options))
        return "\n\n".join(pieces + [options])

    def render_completion(self, profile: KolbProfile, answered_count: int) -> str:
        if answered_count < 12:
            opening = "Con esto ya tengo una base muy buena para arrancar con vos."
        else:
            opening = "Listo, gracias por tomarte este ratito para responder."
        confidence_line = ""
        if profile.confidence is not None:
            confidence_line = f"\nConfianza: {profile.confidence:.2f}."
        return (
            f"{opening} {profile.summary}\n\n"
            f"Estilo Kolb: {profile.style}.\n"
            f"Vector actual: AE={profile.current_vector.AE:.0f}, "
            f"RO={profile.current_vector.RO:.0f}, "
            f"AC={profile.current_vector.AC:.0f}, "
            f"CE={profile.current_vector.CE:.0f}."
            f"{confidence_line}"
        )

    def _friendly_prompt(self, scenario: ScenarioDefinition) -> str:
        return (
            f"Che, te hago una pregunta cortita para conocerte un poco mejor. {scenario['situation']} "
            "Decime con cual opcion te sentis mas identificado."
        )

    def _chunk_intro(
        self,
        chunk: str,
        answered_count: int,
        student_name: str | None,
        student_last_name: str | None,
    ) -> str:
        if answered_count == 0 and chunk == "A":
            full_name = " ".join(part for part in [student_name, student_last_name] if part)
            return (
                f"Hola {full_name}, mucho gusto. "
                "Voy a hacerte unas preguntas cortitas sobre situaciones cotidianas para entender "
                "como aprendes y como acompanarte mejor. Responde una opcion por vez y al final "
                "voy a armar tu perfil Kolb."
            )
        return ""