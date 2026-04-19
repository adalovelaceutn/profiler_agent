from __future__ import annotations

from profiler_agent.config import Settings
from profiler_agent.interview.engine import InterviewEngine
from profiler_agent.llm.huggingface import HuggingFaceLLM


class StubPromptLLM(HuggingFaceLLM):
    def __init__(self, prompt_text: str | None) -> None:
        super().__init__(settings=Settings())
        self.prompt_text = prompt_text
        self.recent_prompts_calls: list[list[str] | None] = []

    async def generate_scenario_prompt(self, scenario, recent_prompts=None):  # type: ignore[override]
        self.recent_prompts_calls.append(recent_prompts)
        return self.prompt_text


async def test_engine_uses_generated_scenario_prompt_when_available() -> None:
    llm = StubPromptLLM("Te pongo una situacion concreta: como actuarias vos aca?")
    engine = InterviewEngine(llm=llm)

    state = await engine.start(student_id="123", student_name="Ada", student_last_name="Lovelace")

    assert state.last_prompt is not None
    assert state.last_prompt.prompt == "Te pongo una situacion concreta: como actuarias vos aca?"
    assert state.prompt_history == ["Te pongo una situacion concreta: como actuarias vos aca?"]
    assert llm.recent_prompts_calls == [[]]


async def test_engine_keeps_fallback_prompt_when_llm_does_not_return_text() -> None:
    llm = StubPromptLLM(None)
    engine = InterviewEngine(llm=llm)

    state = await engine.start(student_id="123", student_name="Ada", student_last_name="Lovelace")

    assert state.last_prompt is not None
    assert "Te compras un electrodomestico complejo y nuevo que nunca usaste." in state.last_prompt.prompt
    assert "situacion bien cotidiana" in state.last_prompt.prompt
    assert state.prompt_history == [state.last_prompt.prompt]
    assert llm.recent_prompts_calls == [[]]