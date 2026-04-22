from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import ValidationError

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import TextPart

from profiler_agent.interview.engine import InterviewEngine
from profiler_agent.interview.repository import InterviewRepository
from profiler_agent.mcp.client import KolbMCPClient
from profiler_agent.models import InterviewState, StudentRecord


@dataclass(slots=True)
class KolbAgentExecutor(AgentExecutor):
    engine: InterviewEngine
    interview_repository: InterviewRepository
    mcp_client: KolbMCPClient

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        user_input = context.get_user_input().strip()
        await updater.submit()
        await updater.start_work()

        existing_state = await self.interview_repository.get(context.task_id)
        if existing_state is None:
            student = self._parse_student_record(user_input)
            if student is None:
                await updater.requires_input(
                    updater.new_agent_message(
                        [
                            TextPart(
                                text=(
                                    "Necesito que me mandes un registro de alumno valido en JSON "
                                    "con id, nombre y apellido para empezar."
                                )
                            )
                        ]
                    )
                )
                return

            state = await self.engine.start(int(student.id), student.nombre, student.apellido)
            await self.interview_repository.save(context.task_id, state)
            prompt_text = self.engine.render_prompt(state)
            await updater.requires_input(updater.new_agent_message([TextPart(text=prompt_text)]))
            return

        state = await self.engine.advance(existing_state, user_input)
        if state.needs_clarification:
            await self.interview_repository.save(context.task_id, state)
            prompt_text = self.engine.render_prompt(state)
            await updater.requires_input(updater.new_agent_message([TextPart(text=prompt_text)]))
            return

        if state.is_complete and state.profile is not None:
            await self.mcp_client.save_profile(state.profile)
            completion_payload = json.dumps(
                {
                    "status": "completed",
                    "student_id": state.profile.student_id,
                    "kolb_style": state.profile.style,
                    "confidence": state.profile.confidence,
                    "answered_scenarios": len(state.answered_scenarios),
                },
                ensure_ascii=False,
            )
            final_message = updater.new_agent_message([TextPart(text=completion_payload)])
            await updater.complete(final_message)
            await self.interview_repository.delete(context.task_id)
            return

        await self.interview_repository.save(context.task_id, state)
        prompt_text = self.engine.render_prompt(state)
        await updater.requires_input(updater.new_agent_message([TextPart(text=prompt_text)]))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        await self.interview_repository.delete(context.task_id)
        await updater.cancel(
            updater.new_agent_message([TextPart(text="La entrevista fue cancelada.")])
        )

    def _parse_student_record(self, user_input: str) -> StudentRecord | None:
        cleaned = user_input.strip()
        if not cleaned:
            return None
        try:
            return StudentRecord.model_validate_json(cleaned)
        except ValidationError:
            return None
