from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field, field_validator


Dimension = Literal["AE", "RO", "AC", "CE"]


def _empty_int_list() -> list[int]:
    return []


def _empty_answer_list() -> list[dict[str, Any]]:
    return []


def _empty_text_list() -> list[str]:
    return []


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


class StudentRecord(BaseModel):
    id: str
    nombre: str
    apellido: str

    @field_validator("id", "nombre", "apellido", mode="before")
    @classmethod
    def _strip_required_text(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("El valor debe ser texto")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El valor no puede estar vacio")
        return cleaned


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
    student_name: str
    student_last_name: str
    pending_scenarios: list[int]
    answered_scenarios: list[int] = Field(default_factory=_empty_int_list)
    current_vector: KolbVector = Field(default_factory=KolbVector)
    last_user_input: str = ""
    is_complete: bool = False
    confidence: float = 0.0
    current_scenario_id: int | None = None
    current_chunk: str | None = None
    last_prompt: ScenarioPrompt | None = None
    prompt_history: list[str] = Field(default_factory=_empty_text_list)
    profile: KolbProfile | None = None
    last_feedback: str | None = None
    answers: list[dict[str, Any]] = Field(default_factory=_empty_answer_list)
    needs_clarification: bool = False
