from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from profiler_agent.config import Settings
from profiler_agent.models import KolbProfile, KolbVector


class KolbProfileNotFoundError(Exception):
    pass


@dataclass(slots=True)
class KolbMCPClient:
    settings: Settings

    @asynccontextmanager
    async def session(self) -> AsyncIterator[ClientSession]:
        transport = self.settings.mcp_transport.strip().lower()

        if transport == "stdio":
            server = StdioServerParameters(
                command=self.settings.mcp_server_command,
                args=self.settings.mcp_server_args,
            )
            async with stdio_client(server) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
            return

        if not self.settings.mcp_server_url:
            raise ValueError("MCP_SERVER_URL es obligatorio cuando MCP_TRANSPORT no es stdio")

        if transport == "sse":
            async with sse_client(
                self.settings.mcp_server_url,
                headers=self.settings.mcp_headers,
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
            return

        if transport in {"streamable-http", "streamable_http", "http"}:
            async with streamablehttp_client(
                self.settings.mcp_server_url,
                headers=self.settings.mcp_headers,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
            return

        raise ValueError(f"MCP_TRANSPORT no soportado: {self.settings.mcp_transport}")

    async def get_profile(self, student_id: int) -> KolbProfile | None:
        async with self.session() as session:
            result = await session.call_tool(
                self.settings.mcp_get_profile_tool,
                arguments={"student_id": student_id},
            )
            if result.isError:
                first_error = self._extract_error(result.content)
                if self._is_legacy_get_profile_error(first_error):
                    result = await session.call_tool(
                        self.settings.mcp_get_profile_tool,
                        arguments={"alumno_id": str(student_id)},
                    )
        if result.isError:
            raise KolbProfileNotFoundError(self._extract_error(result.content))
        data = result.structuredContent or self._extract_json(result.content)
        if not data:
            return None
        if data.get("not_found") is True:
            return None
        return self._to_local_profile(student_id, data)

    async def save_profile(self, profile: KolbProfile) -> dict[str, Any]:
        async with self.session() as session:
            result = await session.call_tool(
                self.settings.mcp_save_profile_tool,
                arguments=self._to_remote_payload(profile),
            )
        if result.isError:
            raise RuntimeError(self._extract_error(result.content))
        return result.structuredContent or self._extract_json(result.content) or {"ok": True}

    def _to_local_profile(self, student_id: int, data: dict[str, Any]) -> KolbProfile:
        raw_profile = data.get("kolb_profile")

        # Soporta payload nuevo: sobre + kolb_profile completo serializado.
        if isinstance(raw_profile, dict) and isinstance(raw_profile.get("current_vector"), dict):
            profile_data = dict(raw_profile)
            profile_data.setdefault("student_id", student_id)
            return KolbProfile.model_validate(profile_data)

        # Soporta formato plano alineado con el esquema SQL (student_profile).
        if "ae_score" in data or "style" in data:
            vector = KolbVector(
                AE=self._to_float(data.get("ae_score")),
                RO=self._to_float(data.get("ro_score")),
                AC=self._to_float(data.get("ac_score")),
                CE=self._to_float(data.get("ce_score")),
            )
            raw_answers = data.get("answers") or []
            answers = [
                {
                    "scenario_id": a.get("scenario_id"),
                    "dimension": a.get("dimension"),
                    "answer": a.get("answer_text", a.get("answer", "")),
                }
                for a in raw_answers
                if isinstance(a, dict)
            ]
            return KolbProfile(
                student_id=data.get("student_id", student_id),
                assessment_name=str(data.get("assessment_name") or "Lovelace Everyday Life Profiling"),
                model_name=str(data.get("model_name") or "Kolb Cycle"),
                current_vector=vector,
                style=str(data.get("style") or ""),
                confidence=self._to_float(data["confidence"]) if data.get("confidence") is not None else None,
                answered_scenarios=data.get("answered_scenarios") or [],
                answers=answers,
                source=str(data.get("source") or "mcp_remote_profile"),
                summary=str(data.get("summary") or ""),
            )

        # Compatibilidad con formato legacy del MCP remoto.
        legacy_profile = raw_profile if isinstance(raw_profile, dict) else {}
        vector = KolbVector(
            AE=self._to_float(legacy_profile.get("activo")),
            RO=self._to_float(legacy_profile.get("reflexivo")),
            AC=self._to_float(legacy_profile.get("teorico")),
            CE=self._to_float(legacy_profile.get("pragmatico")),
        )
        style = str(data.get("kolb_style") or data.get("preferencia_principal") or legacy_profile.get("style") or "")
        confidence = data.get("confidence")
        answered_scenarios = legacy_profile.get("answered_scenarios")
        answers = legacy_profile.get("answers")
        summary = str(legacy_profile.get("summary") or "")
        if not summary:
            evidence = data.get("evidencia") or []
            summary = self._build_remote_summary(evidence)

        return KolbProfile(
            student_id=student_id,
            current_vector=vector,
            style=style,
            confidence=self._to_float(confidence) if confidence is not None else None,
            answered_scenarios=answered_scenarios if isinstance(answered_scenarios, list) else [],
            answers=answers if isinstance(answers, list) else [],
            source="mcp_remote_profile",
            summary=summary,
        )

    def _to_remote_payload(self, profile: KolbProfile) -> dict[str, Any]:
        vector = profile.current_vector.as_dict()
        return {
            "student_id": profile.student_id,
            "assessment_name": profile.assessment_name,
            "model_name": profile.model_name,
            "status": "completed",
            "style": profile.style,
            "confidence": profile.confidence,
            "ae_score": round(vector["AE"], 4),
            "ro_score": round(vector["RO"], 4),
            "ac_score": round(vector["AC"], 4),
            "ce_score": round(vector["CE"], 4),
            "source": profile.source,
            "summary": profile.summary,
            "answers": [
                {
                    "scenario_id": a.get("scenario_id"),
                    "dimension": a.get("dimension"),
                    "answer_text": a.get("answer", ""),
                }
                for a in profile.answers
                if isinstance(a, dict)
            ],
            "answered_scenarios": profile.answered_scenarios,
        }

    def _build_remote_summary(self, evidence: list[Any]) -> str:
        snippets: list[str] = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            text = item.get("texto")
            if isinstance(text, str) and text.strip():
                snippets.append(text.strip())
        return "\n".join(snippets)

    def _extract_error(self, content: list[Any]) -> str:
        if not content:
            return "MCP devolvio un error sin contenido"
        for item in content:
            text = getattr(item, "text", None)
            if text:
                return text
        return "MCP devolvio un error"

    def _extract_json(self, content: list[Any]) -> dict[str, Any] | None:
        for item in content:
            text = getattr(item, "text", None)
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    def _is_legacy_get_profile_error(self, error_message: str) -> bool:
        lowered = error_message.lower()
        return "alumno_id" in lowered and "field required" in lowered

    def _to_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
