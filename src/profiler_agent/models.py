from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


Dimension = Literal["AE", "RO", "AC", "CE"]


class AssessmentOption(TypedDict):
    text: str
    score: int


class ScenarioDefinition(TypedDict):
    id: int
    dimension: Dimension
    situation: str
    options: list[AssessmentOption]


class AssessmentDefinition(TypedDict):
    assessment_name: str
    model: str
    scenarios: list[ScenarioDefinition]


class KolbVector(BaseModel):
    AE: float = 0.0
    RO: float = 0.0
    AC: float = 0.0
    CE: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return self.model_dump()


class ParsedResponse(BaseModel):
    selected_score: int | None = None
    selected_option_index: int | None = None
    rationale: str | None = None
    needs_clarification: bool = False


class ScenarioPrompt(BaseModel):
    scenario_id: int
    chunk: str
    intro: str
    prompt: str
    options: list[str]
    dimension: Dimension


class KolbProfile(BaseModel):
    student_id: str
    assessment_name: str = "Lovelace Everyday Life Profiling"
    model_name: str = "Kolb Cycle"
    current_vector: KolbVector
    style: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    answered_scenarios: list[int]
    answers: list[dict[str, Any]]
    source: str
    summary: str


class InterviewState(BaseModel):
    student_id: str
    pending_scenarios: list[int]
    answered_scenarios: list[int] = Field(default_factory=list)
    current_vector: KolbVector = Field(default_factory=KolbVector)
    last_user_input: str = ""
    is_complete: bool = False
    confidence: float = 0.0
    current_scenario_id: int | None = None
    current_chunk: str | None = None
    last_prompt: ScenarioPrompt | None = None
    profile: KolbProfile | None = None
    last_feedback: str | None = None
    answers: list[dict[str, Any]] = Field(default_factory=list)
    needs_clarification: bool = False
