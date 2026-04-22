from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(
        default=8000,
        validation_alias=AliasChoices("PORT", "APP_PORT"),
    )
    public_base_url: str = Field(
        default="http://localhost:8000",
        alias="PUBLIC_BASE_URL",
    )

    hf_api_key: str | None = Field(default=None, alias="HF_API_KEY")
    hf_api_url: str = Field(
        default="https://router.huggingface.co/v1/chat/completions",
        alias="HF_API_URL",
    )
    hf_model: str = Field(
        default="meta-llama/Llama-3.1-8B-Instruct",
        alias="HF_MODEL",
    )
    hf_temperature: float = Field(default=0.2, alias="HF_TEMPERATURE")
    hf_max_tokens: int = Field(default=200, alias="HF_MAX_TOKENS")

    mcp_transport: str = Field(default="stdio", alias="MCP_TRANSPORT")
    mcp_server_url: str | None = Field(default=None, alias="MCP_SERVER_URL")
    mcp_headers_raw: str = Field(default="{}", alias="MCP_HEADERS")
    mcp_server_command: str = Field(default="python", alias="MCP_SERVER_COMMAND")
    mcp_server_args_raw: str = Field(default="[]", alias="MCP_SERVER_ARGS")
    mcp_get_profile_tool: str = Field(
        default="get_kolb_profile",
        alias="MCP_GET_PROFILE_TOOL",
    )
    mcp_save_profile_tool: str = Field(
        default="actualizar_perfil_kolb",
        alias="MCP_SAVE_PROFILE_TOOL",
    )

    @property
    def mcp_server_args(self) -> list[str]:
        parsed = json.loads(self.mcp_server_args_raw)
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ValueError("MCP_SERVER_ARGS debe ser un JSON array de strings")
        return parsed

    @property
    def mcp_headers(self) -> dict[str, Any]:
        parsed = json.loads(self.mcp_headers_raw)
        if not isinstance(parsed, dict):
            raise ValueError("MCP_HEADERS debe ser un JSON object")
        return parsed


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
