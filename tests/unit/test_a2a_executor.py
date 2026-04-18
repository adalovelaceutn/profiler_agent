from __future__ import annotations

from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, MessageSendParams, Role, TextPart

from profiler_agent.a2a.executor import KolbAgentExecutor
from profiler_agent.models import InterviewState, KolbProfile, KolbVector, ScenarioPrompt


def _build_context(text: str) -> RequestContext:
    return RequestContext(
        request=MessageSendParams(
            message=Message(
                messageId="msg-test",
                role=Role.user,
                parts=[TextPart(text=text)],
            )
        )
    )


def _extract_message_text(event: object) -> str:
    status = getattr(event, "status", None)
    assert status is not None
    message = status.message
    assert message is not None
    parts = message.parts or []
    texts: list[str] = []
    for part in parts:
        payload = part.model_dump(mode="json", by_alias=True)
        text = payload.get("text")
        if isinstance(text, str) and text:
            texts.append(text)
    return "\n".join(texts)


async def _drain_events(queue: EventQueue) -> list[object]:
    events: list[object] = []
    while True:
        try:
            event = await queue.dequeue_event(no_wait=True)
        except Exception:
            break
        events.append(event)
        queue.task_done()
    return events


class StubRepository:
    def __init__(self, initial_state: InterviewState | None = None) -> None:
        self.state = initial_state
        self.saved_state: InterviewState | None = None
        self.deleted_task_id: str | None = None

    async def get(self, task_id: str) -> InterviewState | None:
        return self.state

    async def save(self, task_id: str, state: InterviewState) -> None:
        self.saved_state = state

    async def delete(self, task_id: str) -> None:
        self.deleted_task_id = task_id


class StubEngine:
    def __init__(
        self,
        start_state: InterviewState | None = None,
        next_state: InterviewState | None = None,
        prompt_text: str = "PROMPT",
        completion_text: str = "COMPLETED",
    ) -> None:
        self.start_state = start_state
        self.next_state = next_state
        self.prompt_text = prompt_text
        self.completion_text = completion_text
        self.start_calls: list[tuple[str, str, str]] = []
        self.advance_calls: list[tuple[InterviewState, str]] = []

    async def start(self, student_id: str, student_name: str, student_last_name: str) -> InterviewState:
        self.start_calls.append((student_id, student_name, student_last_name))
        assert self.start_state is not None
        return self.start_state

    async def advance(self, state: InterviewState, user_input: str) -> InterviewState:
        self.advance_calls.append((state, user_input))
        assert self.next_state is not None
        return self.next_state

    def render_prompt(self, state: InterviewState) -> str:
        return self.prompt_text

    def render_completion(self, state: InterviewState) -> str:
        return self.completion_text


class StubMCPClient:
    def __init__(self) -> None:
        self.saved_profiles: list[KolbProfile] = []

    async def save_profile(self, profile: KolbProfile) -> dict[str, bool]:
        self.saved_profiles.append(profile)
        return {"ok": True}

    async def get_profile(self, student_id: str) -> None:
        raise AssertionError("No deberia consultar el perfil antes de entrevistar")


async def test_execute_starts_interview_without_fetching_existing_profile() -> None:
    start_state = InterviewState(
        student_id="123",
        student_name="Ada",
        student_last_name="Lovelace",
        pending_scenarios=[1],
        last_prompt=ScenarioPrompt(
            scenario_id=1,
            chunk="A",
            intro="Hola Ada Lovelace",
            prompt="Pregunta",
            options=["uno", "dos", "tres"],
            dimension="AE",
        ),
    )
    repository = StubRepository()
    engine = StubEngine(start_state=start_state, prompt_text="PROMPT")
    mcp_client = StubMCPClient()
    executor = KolbAgentExecutor(engine=engine, interview_repository=repository, mcp_client=mcp_client)
    context = _build_context('{"id":"123","nombre":"Ada","apellido":"Lovelace"}')
    queue = EventQueue()

    await executor.execute(context, queue)
    events = await _drain_events(queue)

    assert engine.start_calls == [("123", "Ada", "Lovelace")]
    assert repository.saved_state == start_state
    assert mcp_client.saved_profiles == []
    assert getattr(events[-1], "status").state == "input-required"
    assert _extract_message_text(events[-1]) == "PROMPT"


async def test_execute_saves_profile_when_interview_finishes() -> None:
    profile = KolbProfile(
        student_id="123",
        current_vector=KolbVector(AE=8, RO=2, AC=6, CE=4),
        style="Convergente",
        confidence=0.91,
        answered_scenarios=[1, 2, 3],
        answers=[],
        source="test",
        summary="Resumen final.",
    )
    existing_state = InterviewState(
        student_id="123",
        student_name="Ada",
        student_last_name="Lovelace",
        pending_scenarios=[4],
    )
    completed_state = InterviewState(
        student_id="123",
        student_name="Ada",
        student_last_name="Lovelace",
        pending_scenarios=[],
        is_complete=True,
        profile=profile,
    )
    repository = StubRepository(initial_state=existing_state)
    engine = StubEngine(next_state=completed_state, completion_text="COMPLETED")
    mcp_client = StubMCPClient()
    executor = KolbAgentExecutor(engine=engine, interview_repository=repository, mcp_client=mcp_client)
    context = _build_context("respuesta final")
    queue = EventQueue()

    await executor.execute(context, queue)
    events = await _drain_events(queue)

    assert len(engine.advance_calls) == 1
    assert mcp_client.saved_profiles == [profile]
    assert repository.deleted_task_id == context.task_id
    assert getattr(events[-1], "status").state == "completed"
    assert _extract_message_text(events[-1]) == "COMPLETED"