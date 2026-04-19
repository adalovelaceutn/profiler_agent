from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, StateGraph

from profiler_agent.assessment_data import ASSESSMENTS
from profiler_agent.interview.prompts import CHUNK_TRANSITIONS, InterviewPrompts
from profiler_agent.llm.huggingface import HuggingFaceLLM
from profiler_agent.models import InterviewState, KolbProfile, ParsedResponse, ScenarioDefinition, ScenarioPrompt


CHUNK_ORDER: dict[str, list[int]] = {
    "A": [1, 4, 9, 12],
    "B": [2, 3, 7, 10],
    "C": [5, 6, 8, 11],
}

STYLE_MAP = {
    ("AC", "AE"): "Convergente",
    ("CE", "RO"): "Divergente",
    ("AC", "RO"): "Asimilador",
    ("CE", "AE"): "Acomodador",
}


@dataclass(slots=True)
class InterviewEngine:
    llm: HuggingFaceLLM
    prompts: InterviewPrompts = field(default_factory=InterviewPrompts)
    graph: Any = field(init=False)

    def __post_init__(self) -> None:
        graph = StateGraph(InterviewState)
        graph.add_node("scenario_selector", self._scenario_selector)
        graph.add_node("conversation_agent", self._conversation_agent)
        graph.add_node("response_parser", self._response_parser)
        graph.add_node("incremental_scorer", self._incremental_scorer)
        graph.add_node("finalizer", self._finalizer)
        graph.set_entry_point("scenario_selector")
        graph.add_conditional_edges(
            "scenario_selector",
            self._route_after_selection,
            {
                "conversation_agent": "conversation_agent",
                "response_parser": "response_parser",
                "finalizer": "finalizer",
            },
        )
        graph.add_edge("conversation_agent", END)
        graph.add_edge("response_parser", "incremental_scorer")
        graph.add_conditional_edges(
            "incremental_scorer",
            self._route_after_scoring,
            {
                "scenario_selector": "scenario_selector",
                "conversation_agent": "conversation_agent",
                "finalizer": "finalizer",
            },
        )
        graph.add_edge("finalizer", END)
        self.graph = graph.compile()

    async def start(self, student_id: str, student_name: str, student_last_name: str) -> InterviewState:
        state = InterviewState(
            student_id=student_id,
            student_name=student_name,
            student_last_name=student_last_name,
            pending_scenarios=list(self._scenarios_by_id().keys()),
        )
        result = await self.graph.ainvoke(state)
        return InterviewState.model_validate(result)

    async def advance(self, state: InterviewState, user_input: str) -> InterviewState:
        state.last_user_input = user_input
        result = await self.graph.ainvoke(state)
        return InterviewState.model_validate(result)

    async def _scenario_selector(self, state: InterviewState) -> InterviewState:
        if state.is_complete or not state.pending_scenarios:
            state.is_complete = True
            return state

        if state.last_prompt is not None and state.last_user_input:
            return state

        next_scenario_id = self._pick_next_scenario(state)
        if next_scenario_id is None:
            state.is_complete = True
            return state

        chunk = self._chunk_for_scenario(next_scenario_id)
        scenario = self._scenarios_by_id()[next_scenario_id]
        transition = None
        if state.answered_scenarios:
            last_answered = state.answered_scenarios[-1]
            previous_chunk = self._chunk_for_scenario(last_answered)
            if previous_chunk != chunk:
                transition = CHUNK_TRANSITIONS.get(previous_chunk)

        generated_prompt = await self.llm.generate_scenario_prompt(
            scenario,
            recent_prompts=state.prompt_history[-3:],
        )

        state.current_scenario_id = next_scenario_id
        state.current_chunk = chunk
        state.last_prompt = self.prompts.build_scenario_prompt(
            scenario=scenario,
            chunk=chunk,
            answered_count=len(state.answered_scenarios),
            student_name=state.student_name,
            student_last_name=state.student_last_name,
            transition=transition,
            prompt_text=generated_prompt,
        )
        state.prompt_history.append(state.last_prompt.prompt)
        state.needs_clarification = False
        return state

    async def _conversation_agent(self, state: InterviewState) -> InterviewState:
        return state

    async def _response_parser(self, state: InterviewState) -> InterviewState:
        if state.current_scenario_id is None:
            return state

        scenario = self._scenarios_by_id()[state.current_scenario_id]
        parsed = await self.llm.parse_option_response(state.last_user_input, scenario)
        if parsed.needs_clarification:
            state.needs_clarification = True
            state.last_feedback = self.prompts.clarification_feedback()
            return state

        state.needs_clarification = False
        state.last_feedback = parsed.rationale
        state.answers.append(
            {
                "scenario_id": scenario["id"],
                "dimension": scenario["dimension"],
                "answer": state.last_user_input,
                "selected_option_index": parsed.selected_option_index,
                "selected_score": parsed.selected_score,
            }
        )
        return state

    async def _incremental_scorer(self, state: InterviewState) -> InterviewState:
        if state.needs_clarification or not state.answers:
            return state

        latest = state.answers[-1]
        scenario_id = latest["scenario_id"]
        if scenario_id not in state.pending_scenarios:
            return state

        dimension = latest["dimension"]
        current_value = getattr(state.current_vector, dimension)
        setattr(state.current_vector, dimension, current_value + float(latest["selected_score"]))
        state.pending_scenarios.remove(scenario_id)
        state.answered_scenarios.append(scenario_id)
        state.current_scenario_id = None
        state.last_user_input = ""
        state.last_prompt = None
        state.confidence = self._compute_confidence(state)

        if self._should_exit_early(state):
            state.is_complete = True
        elif not state.pending_scenarios:
            state.is_complete = True
        return state

    async def _finalizer(self, state: InterviewState) -> InterviewState:
        state.is_complete = True
        state.profile = KolbProfile(
            student_id=state.student_id,
            current_vector=state.current_vector,
            style=self._infer_style(state.current_vector.as_dict()),
            confidence=state.confidence,
            answered_scenarios=state.answered_scenarios,
            answers=state.answers,
            source="generated_via_guided_interview",
            summary=self._build_summary(state),
        )
        return state

    def _route_after_selection(self, state: InterviewState) -> str:
        if state.is_complete:
            return "finalizer"
        if state.last_user_input:
            return "response_parser"
        return "conversation_agent"

    def _route_after_scoring(self, state: InterviewState) -> str:
        if state.is_complete:
            return "finalizer"
        if state.needs_clarification:
            return "conversation_agent"
        return "scenario_selector"

    def render_prompt(self, state: InterviewState) -> str:
        if state.needs_clarification and state.last_prompt is not None:
            return self.prompts.render_prompt(state.last_prompt, prefix=state.last_feedback)
        if state.last_prompt is None:
            raise ValueError("No hay prompt activo para renderizar")
        return self.prompts.render_prompt(state.last_prompt)

    def render_completion(self, state: InterviewState) -> str:
        if state.profile is None:
            raise ValueError("No hay perfil final para renderizar")
        return self.prompts.render_completion(state.profile, len(state.answered_scenarios))

    def _pick_next_scenario(self, state: InterviewState) -> int | None:
        chunk_priority = [chunk for chunk in ["A", "B", "C"] if any(item in state.pending_scenarios for item in CHUNK_ORDER[chunk])]
        if not chunk_priority:
            return None
        active_chunk = chunk_priority[0]
        candidates = [scenario_id for scenario_id in CHUNK_ORDER[active_chunk] if scenario_id in state.pending_scenarios]
        if len(candidates) == 1:
            return candidates[0]

        vector = state.current_vector.as_dict()
        scored_candidates: list[tuple[float, int]] = []
        for scenario_id in candidates:
            scenario = self._scenarios_by_id()[scenario_id]
            dimension = scenario["dimension"]
            paired_dimension = self._paired_dimension(dimension)
            uncertainty = abs(vector[dimension] - vector[paired_dimension])
            scored_candidates.append((uncertainty, scenario_id))
        scored_candidates.sort(key=lambda item: (item[0], item[1]))
        return scored_candidates[0][1]

    def _compute_confidence(self, state: InterviewState) -> float:
        answered_ratio = len(state.answered_scenarios) / 12.0
        vector = state.current_vector.as_dict()
        pair_gap_1 = abs(vector["AC"] - vector["CE"])
        pair_gap_2 = abs(vector["AE"] - vector["RO"])
        separation = min(pair_gap_1, pair_gap_2) / 8.0
        ordered = sorted(vector.values(), reverse=True)
        dominance = (ordered[0] - ordered[2]) / max(ordered[0], 1.0)
        score = (
            (answered_ratio * 0.35)
            + (min(separation, 1.0) * 0.45)
            + (min(max(dominance, 0.0), 1.0) * 0.20)
        )
        if len(state.answered_scenarios) >= 8 and separation >= 0.75 and dominance >= 0.7:
            score += 0.03
        return min(0.99, round(score, 2))

    def _should_exit_early(self, state: InterviewState) -> bool:
        if len(state.answered_scenarios) < 8:
            return False
        vector = state.current_vector.as_dict()
        dominant = sorted(vector.items(), key=lambda item: item[1], reverse=True)
        return state.confidence >= 0.85 and (dominant[0][1] - dominant[2][1]) >= 6

    def _infer_style(self, vector: dict[str, float]) -> str:
        perception = "AC" if vector["AC"] >= vector["CE"] else "CE"
        processing = "AE" if vector["AE"] >= vector["RO"] else "RO"
        return STYLE_MAP[(perception, processing)]

    def _build_summary(self, state: InterviewState) -> str:
        style = self._infer_style(state.current_vector.as_dict())
        if style == "Asimilador":
            return "Tu perfil muestra que primero buscas entender el por que y ordenar las ideas antes de lanzarte." 
        if style == "Convergente":
            return "Tu perfil muestra que te sentis comodo cuando entiendes el problema y despues lo llevas rapido a una accion concreta."
        if style == "Divergente":
            return "Tu perfil muestra que observas bien el contexto, conectas perspectivas y aprendes mucho desde la experiencia humana."
        return "Tu perfil muestra que aprendes mejor cuando probas, ajustas en marcha y convertis la experiencia en accion."

    def _chunk_for_scenario(self, scenario_id: int) -> str:
        for chunk, items in CHUNK_ORDER.items():
            if scenario_id in items:
                return chunk
        raise ValueError(f"Escenario desconocido: {scenario_id}")

    def _paired_dimension(self, dimension: str) -> str:
        if dimension == "AE":
            return "RO"
        if dimension == "RO":
            return "AE"
        if dimension == "AC":
            return "CE"
        return "AC"

    def _scenarios_by_id(self) -> dict[int, ScenarioDefinition]:
        scenarios = ASSESSMENTS[0]["scenarios"]
        return {scenario["id"]: scenario for scenario in scenarios}
