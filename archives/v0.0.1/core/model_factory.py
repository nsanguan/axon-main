"""
model_factory — resolve a 'provider:model_name' spec into a PydanticAI model object.

Format:
    <provider>:<model_name>

Supported providers
-------------------
  ollama     → OllamaModel(model_name, provider=OllamaProvider(base_url=...))
               base_url read from settings.ollama_base_url / OLLAMA_BASE_URL
  anthropic  → passed as-is to Agent (PydanticAI reads ANTHROPIC_API_KEY)
  openai     → passed as-is to Agent (PydanticAI reads OPENAI_API_KEY)
  google-gla → passed as-is to Agent (PydanticAI reads GOOGLE_API_KEY / GEMINI_API_KEY)
  groq       → passed as-is to Agent (PydanticAI reads GROQ_API_KEY)
  mistral    → passed as-is to Agent (PydanticAI reads MISTRAL_API_KEY)
  cohere     → passed as-is to Agent (PydanticAI reads CO_API_KEY)

Examples
--------
  "ollama:gemma4:e4b"              → OllamaModel("gemma4:e4b", ...)
  "anthropic:claude-sonnet-4-6"    → str passed directly to Agent
  "openai:gpt-4o"                  → str passed directly to Agent
  "google-gla:gemini-2.0-flash"    → str passed directly to Agent
  "groq:llama-3.3-70b-versatile"   → str passed directly to Agent
"""

from __future__ import annotations

from typing import Union

# PydanticAI's Agent accepts either a model string or a Model instance
ModelSpec = Union[str, object]

# Providers that PydanticAI handles natively via string prefix (no extra config needed)
_PASSTHROUGH_PROVIDERS = {
    "anthropic",
    "openai",
    "google-gla",
    "google-vertex",
    "groq",
    "mistral",
    "cohere",
    "bedrock",
    "azure",
}


def build_model(model_spec: str) -> ModelSpec:
    """
    Parse *model_spec* and return a PydanticAI-compatible model.

    For providers in ``_PASSTHROUGH_PROVIDERS`` the original string is returned
    unchanged — PydanticAI resolves the provider and reads the API key from the
    environment automatically.

    For ``ollama`` an ``OllamaModel`` instance is returned, configured with
    ``settings.ollama_base_url``.

    Raises ``ValueError`` if *model_spec* contains no ``:`` separator and is
    not a recognised bare model name.
    """
    if ":" not in model_spec:
        raise ValueError(
            f"Invalid model spec {model_spec!r}. "
            "Expected 'provider:model_name', e.g. 'ollama:gemma4:e4b' or "
            "'anthropic:claude-sonnet-4-6'."
        )

    # Split only on the FIRST colon so model names like 'gemma4:e4b' are preserved
    provider, model_name = model_spec.split(":", 1)
    provider = provider.lower().strip()

    if provider == "ollama":
        from pydantic_ai.models.ollama import OllamaModel
        from pydantic_ai.providers.ollama import OllamaProvider

        # Import here to avoid circular import — settings already loaded by caller
        from core.config import settings

        return OllamaModel(
            model_name,
            provider=OllamaProvider(base_url=settings.ollama_base_url),
        )

    if provider in _PASSTHROUGH_PROVIDERS:
        # Return the full original string — PydanticAI parses it natively
        return model_spec

    raise ValueError(
        f"Unknown provider {provider!r} in model spec {model_spec!r}. "
        f"Supported providers: ollama, {', '.join(sorted(_PASSTHROUGH_PROVIDERS))}."
    )
