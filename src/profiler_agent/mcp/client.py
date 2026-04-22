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
        raw_profile = data.get("kolb_profile", {})
        vector = KolbVector(
            AE=float(raw_profile.get("activo", 0.0)),
            RO=float(raw_profile.get("reflexivo", 0.0)),
            AC=float(raw_profile.get("teorico", 0.0)),
            CE=float(raw_profile.get("pragmatico", 0.0)),
        )
        style = str(data.get("preferencia_principal") or "")
        evidence = data.get("evidencia") or []
        summary = self._build_remote_summary(evidence)
        return KolbProfile(
            student_id=student_id,
            current_vector=vector,
            style=style,
            confidence=None,
            answered_scenarios=[],
            answers=[],
            source="mcp_remote_profile",
            summary=summary,
        )

    def _to_remote_payload(self, profile: KolbProfile) -> dict[str, Any]:
        vector = profile.current_vector.as_dict()
        total = sum(vector.values()) or 1.0
        return {
            "alumno_id": str(profile.student_id),
            "activo": round(vector["AE"] / total, 4),
            "reflexivo": round(vector["RO"] / total, 4),
            "teorico": round(vector["AC"] / total, 4),
            "pragmatico": round(vector["CE"] / total, 4),
            "evidencia_texto": profile.summary,
            "origen": "entrevista_a2a",
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
