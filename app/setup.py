"""Interactive first-run configuration for OpenManus-Lite.

Mirrors a Hermes-style setup: the user is prompted for a base URL and API key,
then available models are auto-detected from the provider and the user picks
one. The result is written to ``config/config.toml`` and the live config is
reloaded so the agent can start immediately.
"""
from __future__ import annotations

import sys

from openai import OpenAI

from app.config import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "config" / "config.toml"


def _prompt(text: str, default: str = "") -> str:
    try:
        if default:
            val = input(f"{text} [{default}]: ").strip()
            return val or default
        return input(f"{text}: ").strip()
    except EOFError:
        return default


def config_needs_setup() -> bool:
    """True when no usable API key is present in the loaded config."""
    from app.config import config

    llm = config.llm.get("default")
    if not llm:
        return True
    key = (llm.api_key or "").strip()
    if not key or key.startswith("sk-") and "..." in key:
        return True
    return False


def fetch_models(base_url: str, api_key: str, timeout: int = 20) -> list[str]:
    """Auto-detect models from an OpenAI-compatible provider's /v1/models."""
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        data = client.models.list()
        return [m.id for m in data.data]
    except Exception as e:  # network/permission issues shouldn't crash setup
        print(f"  ! Could not auto-detect models: {e}")
        return []


def run_setup() -> None:
    print("OpenManus-Lite setup")
    print("Provide your AI provider credentials (any OpenAI-compatible API).\n")

    base_url = _prompt("Base URL", "https://api.openai.com/v1")
    api_key = _prompt("API key")
    if not api_key:
        print("API key is required. Aborting.")
        sys.exit(1)

    print("Detecting available models from provider...")
    models = fetch_models(base_url, api_key)
    if models:
        shown = models[:50]
        for i, m in enumerate(shown, 1):
            print(f"  {i:>3}. {m}")
        default_model = shown[0] if shown else "gpt-4o"
        try:
            choice = _prompt(
                "Select a model (number, or type a model id)",
                default_model,
            )
        except EOFError:
            choice = default_model
        if choice.isdigit() and 1 <= int(choice) <= len(shown):
            model = shown[int(choice) - 1]
        else:
            model = choice or default_model
    else:
        try:
            model = _prompt("Model id (auto-detect failed, enter manually)", "gpt-4o")
        except EOFError:
            model = "gpt-4o"

    max_tokens = _prompt("Max tokens", "4096")
    temperature = _prompt("Temperature", "0.0")

    toml_text = (
        "# OpenManus-Lite configuration (created by interactive setup)\n"
        "[llm]\n"
        f'base_url = "{base_url}"\n'
        f'api_key = "{api_key}"\n'
        f'model = "{model}"\n'
        f"max_tokens = {max_tokens}\n"
        f"temperature = {temperature}\n"
        'api_type = "openai"\n'
        "\n"
        "[sandbox]\n"
        "use_sandbox = false\n"
        "timeout = 300\n"
    )
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(toml_text)
    print(f"\nSaved configuration to {CONFIG_PATH}")
    print(f"Selected model: {model}")
