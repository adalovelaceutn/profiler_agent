from __future__ import annotations

import json
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import httpx

from profiler_agent.config import Settings
from profiler_agent.llm.prompts import HuggingFacePromptBuilder
from profiler_agent.models import ParsedResponse, ScenarioDefinition


@dataclass(slots=True)
class HuggingFaceLLM:
    settings: Settings
    model_name: str | None = None
    prompt_builder: HuggingFacePromptBuilder = field(default_factory=HuggingFacePromptBuilder)

    @property
    def active_model(self) -> str:
        return self.model_name or self.settings.hf_model

    async def parse_option_response(
        self,
        user_input: str,
        scenario: ScenarioDefinition,
    ) -> ParsedResponse:
        deterministic = self._deterministic_parse(user_input, scenario)
        if deterministic.selected_option_index is not None or not self.settings.hf_api_key:
            return deterministic

        prompt = self.prompt_builder.parser_user_prompt(user_input, scenario)
        payload = {
            "model": self.active_model,
            "messages": [
                {
                    "role": "system",
                    "content": self.prompt_builder.parser_system_prompt(),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": self.settings.hf_temperature,
            "max_tokens": self.settings.hf_max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.settings.hf_api_key}"}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self.settings.hf_api_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                option_index = data.get("selected_option_index")
                if option_index in (0, 1, 2):
                    return ParsedResponse(
                        selected_option_index=option_index,
                        selected_score=scenario["options"][option_index]["score"],
                        rationale=data.get("rationale"),
                        needs_clarification=False,
                    )
        except Exception:
            return deterministic

        return ParsedResponse(needs_clarification=True)

    def _deterministic_parse(
        self,
        user_input: str,
        scenario: ScenarioDefinition,
    ) -> ParsedResponse:
        cleaned = user_input.strip().lower()
        if cleaned in {"1", "opcion 1", "a", "primera"}:
            return self._from_index(0, scenario, "Coincidencia directa por indice")
        if cleaned in {"2", "opcion 2", "b", "segunda"}:
            return self._from_index(1, scenario, "Coincidencia directa por indice")
        if cleaned in {"3", "opcion 3", "c", "tercera"}:
            return self._from_index(2, scenario, "Coincidencia directa por indice")

        best_index = None
        best_score = 0.0
        for index, option in enumerate(scenario["options"]):
            similarity = SequenceMatcher(None, cleaned, option["text"].lower()).ratio()
            if option["text"].lower() in cleaned:
                similarity += 0.35
            if similarity > best_score:
                best_index = index
                best_score = similarity

        if best_index is not None and best_score >= 0.42:
            return self._from_index(best_index, scenario, f"Match difuso {best_score:.2f}")

        return ParsedResponse(needs_clarification=True)

    def _from_index(
        self,
        index: int,
        scenario: ScenarioDefinition,
        rationale: str,
    ) -> ParsedResponse:
        return ParsedResponse(
            selected_option_index=index,
            selected_score=scenario["options"][index]["score"],
            rationale=rationale,
            needs_clarification=False,
        )
