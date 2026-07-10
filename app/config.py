"""Configuration loader (TOML)."""
from pathlib import Path
from typing import Dict, Optional

import tomllib
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


class LLMSettings(BaseModel):
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    max_tokens: int = 4096
    temperature: float = 0.0
    api_type: str = "openai"


class SandboxSettings(BaseModel):
    use_sandbox: bool = False
    timeout: int = 300


class AppConfig(BaseModel):
    llm: Dict[str, LLMSettings] = Field(default_factory=dict)
    sandbox: Optional[SandboxSettings] = None


class Config:
    """Singleton-ish config loader."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = cls._load()
        return cls._instance

    @staticmethod
    def _load() -> AppConfig:
        path = PROJECT_ROOT / "config" / "config.toml"
        if not path.exists():
            path = PROJECT_ROOT / "config" / "config.example.toml"
        if not path.exists():
            raise FileNotFoundError("No configuration file found in config/")
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        base = raw.get("llm", {})
        default = base.get("default", base) if isinstance(base.get("default"), dict) else base
        llm: Dict[str, LLMSettings] = {"default": LLMSettings(**default)}
        for name, cfg in base.items():
            if isinstance(cfg, dict) and name != "default":
                merged = {**default, **cfg}
                llm[name] = LLMSettings(**merged)
        sandbox = SandboxSettings(**raw["sandbox"]) if raw.get("sandbox") else None
        return AppConfig(llm=llm, sandbox=sandbox)

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        return self._config.llm

    @property
    def sandbox(self):
        return self._config.sandbox

    @property
    def workspace_root(self) -> Path:
        return WORKSPACE_ROOT

    @property
    def root_path(self) -> Path:
        return PROJECT_ROOT


config = Config()
