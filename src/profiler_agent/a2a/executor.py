from __future__ import annotations

from dataclasses import dataclass

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import Part, TextPart

from profiler_agent.interview.engine import InterviewEngine
from profiler_agent.interview.repository import InterviewRepository
from profiler_agent.mcp.client import KolbMCPClient, KolbProfileNotFoundError
from profiler_agent.models import InterviewState


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
            student_id = self._extract_student_id(user_input)
            if not student_id:
                await updater.requires_input(
                    updater.new_agent_message([TextPart(text="Necesito que me mandes un id_alumno valido para empezar.")])
                )
                return

            try:
                profile = await self.mcp_client.get_profile(student_id)
            except KolbProfileNotFoundError:
                profile = None

            if profile is not None:
                message = updater.new_agent_message(
                    [TextPart(text=self._render_existing_profile(profile.model_dump()))]
                )
                await updater.complete(message)
                return

            state = await self.engine.start(student_id)
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
            final_message = updater.new_agent_message(
                [TextPart(text=self.engine.render_completion(state))]
            )
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

    def _extract_student_id(self, user_input: str) -> str | None:
        cleaned = user_input.strip()
        if not cleaned:
            return None
        prefixes = ["id_alumno:", "id_alumno=", "student_id:", "student_id="]
        lowered = cleaned.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                return cleaned[len(prefix):].strip()
        return cleaned.split()[0] if " " not in cleaned else None

    def _render_existing_profile(self, profile: dict) -> str:
        vector = profile["current_vector"]
        lines = [
            f"Encontre el perfil Kolb del alumno {profile['student_id']} en el servidor MCP.\n\n"
            f"Estilo: {profile['style']}.\n"
            f"Vector: AE={vector['AE']}, RO={vector['RO']}, AC={vector['AC']}, CE={vector['CE']}."
        ]
        if profile.get('summary'):
            lines.append(f"\nResumen: {profile['summary']}")
        if profile.get('confidence') is not None:
            lines.append(f"\nConfianza: {profile['confidence']}.")
        return ''.join(lines)
