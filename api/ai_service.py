"""LLM integration for formula parsing and explanation.

Supports Azure OpenAI (preferred when configured), direct OpenAI, xAI Grok, and an
offline mock provider for local testing without API keys.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

from openai import AsyncAzureOpenAI, AsyncOpenAI

AIProvider = Literal["azure", "openai", "xai", "mock"]


class AIConfigurationError(RuntimeError):
    """Raised when no AI provider is configured or required settings are missing."""


@dataclass(frozen=True)
class AISettings:
    provider: AIProvider
    parse_model: str
    translate_model: str
    endpoint: str | None = None
    api_version: str | None = None


_PARSE_SYSTEM = """\
You are an expert professional hair colorist and formula specialist.

Hair level scale: 1 (black) → 12 (lightest blonde).

service_intent values:
- "tone_deposit"   → depositing tone, same or darker level, no lift
- "lift_deposit"   → lifting 1–3 levels while depositing color
- "gray_coverage"  → client has gray/white hair that needs coverage
- "corrective"     → fixing a previous color mistake
- "fashion"        → vivid, non-natural fashion colors

Infer service_intent from context clues (gray percentage > 0 → likely gray_coverage, etc.).

Return ONLY valid compact JSON. No markdown fences, no explanation text."""

_TRANSLATE_SYSTEM = """\
You are an expert professional hair colorist specializing in cross-brand formula translation.

Tone mapping reference (approximate equivalents across systems):
- Natural/Neutral:   Wella /0  | Redken N   | Schwarzkopf -0  | Matrix N
- Ash/Cool:          Wella /1  | Redken A   | Schwarzkopf -1  | Matrix A
- Iridescent:        Wella /2  | Redken I   | Schwarzkopf -2
- Gold:              Wella /3  | Redken G   | Schwarzkopf -3  | Matrix G
- Red:               Wella /4  | Redken R   | Schwarzkopf -4  | Matrix R
- Mahogany:          Wella /5  | Redken RO  | Schwarzkopf -5  | Matrix M
- Violet:            Wella /6  | Redken V   | Schwarzkopf -6  | Matrix V
- Brown:             Wella /7  | Redken B   | Schwarzkopf -7  | Matrix B
- Pearl:             Wella /8  | Redken P   | Schwarzkopf -8
- Warm Brown:        Wella /7  | Redken NW  | Matrix W

Match level number exactly. Match tone family as closely as possible.

Return ONLY valid compact JSON. No markdown, no explanation outside the translation_notes field."""


from api.backend import env, is_production_environment


def _env(name: str, default: str | None = None) -> str | None:
    return env(name, default)


def _mock_allowed() -> bool:
    if not is_production_environment():
        return True
    return (_env("AI_ALLOW_MOCK") or "").lower() in {"1", "true", "yes", "on"}


def _reject_mock_in_production() -> None:
    if is_production_environment() and not _mock_allowed():
        raise AIConfigurationError(
            "Mock AI is disabled in production. Configure Azure OpenAI "
            "(AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY), OPENAI_API_KEY, or "
            "XAI_API_KEY, or set AI_ALLOW_MOCK=1 for an explicit offline deployment."
        )


def resolve_ai_provider() -> AIProvider:
    """Pick the active AI provider from AI_PROVIDER or available credentials."""
    explicit = (_env("AI_PROVIDER") or "").lower()
    if explicit == "mock":
        _reject_mock_in_production()
        return "mock"
    if explicit in {"azure", "openai", "xai"}:
        return explicit  # type: ignore[return-value]
    if _env("AZURE_OPENAI_ENDPOINT") and _env("AZURE_OPENAI_API_KEY"):
        return "azure"
    if _env("OPENAI_API_KEY"):
        return "openai"
    if _env("XAI_API_KEY"):
        return "xai"
    _reject_mock_in_production()
    return "mock"


def get_ai_settings() -> AISettings:
    """Return resolved provider settings for status endpoints and tests."""
    provider = resolve_ai_provider()
    if provider == "mock":
        return AISettings(
            provider="mock",
            parse_model="offline-mock",
            translate_model="offline-mock",
        )
    if provider == "azure":
        endpoint = _env("AZURE_OPENAI_ENDPOINT")
        api_key = _env("AZURE_OPENAI_API_KEY")
        if not endpoint or not api_key:
            raise AIConfigurationError(
                "Azure OpenAI requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY."
            )
        chat_deployment = (
            _env("AZURE_OPENAI_CHAT_DEPLOYMENT")
            or _env("AZURE_OPENAI_DEPLOYMENT")
            or "gpt-4o-mini"
        )
        translate_deployment = (
            _env("AZURE_OPENAI_TRANSLATE_DEPLOYMENT")
            or _env("AZURE_OPENAI_CHAT_DEPLOYMENT")
            or _env("AZURE_OPENAI_DEPLOYMENT")
            or "gpt-4o"
        )
        return AISettings(
            provider="azure",
            parse_model=chat_deployment,
            translate_model=translate_deployment,
            endpoint=endpoint,
            api_version=_env("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
    if provider == "openai":
        if not _env("OPENAI_API_KEY"):
            raise AIConfigurationError("OpenAI requires OPENAI_API_KEY.")
        chat_model = _env("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        translate_model = _env("OPENAI_TRANSLATE_MODEL") or _env("OPENAI_CHAT_MODEL", "gpt-4o")
        return AISettings(
            provider="openai",
            parse_model=chat_model,
            translate_model=translate_model,
            endpoint=_env("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
    if not _env("XAI_API_KEY"):
        raise AIConfigurationError("xAI requires XAI_API_KEY.")
    return AISettings(
        provider="xai",
        parse_model=_env("XAI_CHAT_MODEL", "grok-3-mini"),
        translate_model=_env("XAI_TRANSLATE_MODEL", "grok-3"),
        endpoint="https://api.x.ai/v1",
    )


def _client():
    settings = get_ai_settings()
    if settings.provider == "azure":
        assert settings.endpoint is not None
        assert settings.api_version is not None
        return AsyncAzureOpenAI(
            api_key=_env("AZURE_OPENAI_API_KEY"),
            azure_endpoint=settings.endpoint,
            api_version=settings.api_version,
        )
    if settings.provider == "openai":
        return AsyncOpenAI(
            api_key=_env("OPENAI_API_KEY"),
            base_url=settings.endpoint,
        )
    return AsyncOpenAI(
        api_key=_env("XAI_API_KEY"),
        base_url=settings.endpoint,
    )


async def parse_formula_request(
    user_input: str,
    color_line: str,
    canonical_key: str,
) -> dict[str, Any]:
    """Parse natural-language stylist input into structured engine parameters."""
    settings = get_ai_settings()
    if settings.provider == "mock":
        from api.ai_mock import mock_parse_formula_request

        return mock_parse_formula_request(user_input, color_line, canonical_key)
    prompt = (
        f"The stylist is working with: {color_line}\n\n"
        f"Stylist input:\n{user_input}\n\n"
        f"Return JSON with ALL applicable fields:\n"
        f'{{"shade":"<code for {color_line}>","current_level":<1-12>,"gray":<0-100>,'
        f'"texture":"fine|medium|coarse","service_intent":"...","desired_level":<1-12>,'
        f'"porosity":<1-10 default 5>,"elasticity":<1-10 default 6>,"line":"{color_line}"}}'
    )
    resp = await _client().chat.completions.create(
        model=settings.parse_model,
        messages=[
            {"role": "system", "content": _PARSE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return json.loads(resp.choices[0].message.content)


async def explain_formula(
    formula_result: dict[str, Any],
    user_input: str,
    color_line: str,
    mode: str = "formula",
    translation_notes: str | None = None,
) -> str:
    """Generate a concise professional explanation of the formula."""
    settings = get_ai_settings()
    if settings.provider == "mock":
        from api.ai_mock import mock_explain_formula

        return mock_explain_formula(
            formula_result,
            user_input,
            color_line,
            mode=mode,
            translation_notes=translation_notes,
        )
    if mode == "translate":
        context = (
            f"A stylist wants to translate this formula into {color_line}:\n{user_input}\n\n"
            f"Translation analysis: {translation_notes or 'see formula'}\n\n"
        )
    else:
        context = f"Stylist described: {user_input}\n\n"

    prompt = (
        f"{context}"
        f"Formula engine output:\n{json.dumps(formula_result, indent=2)}\n\n"
        "Write a 3–5 sentence professional explanation covering:\n"
        "1. Specific products selected and the clinical reason\n"
        "2. Developer strength and mix ratio rationale\n"
        "3. Expected result and any key application notes\n\n"
        "Be direct and specific. Professional salon language. No bullet points."
    )
    resp = await _client().chat.completions.create(
        model=settings.parse_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior hair color educator explaining formulas to stylists. "
                    "Be concise, specific, and professional."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


async def translate_formula(
    source_formula: str,
    source_line: str | None,
    target_line: str,
    target_canonical_key: str,
) -> dict[str, Any]:
    """Translate a formula from one color line to another."""
    settings = get_ai_settings()
    if settings.provider == "mock":
        from api.ai_mock import mock_translate_formula

        return mock_translate_formula(
            source_formula,
            source_line,
            target_line,
            target_canonical_key,
        )
    source_ctx = f"Source line: {source_line}" if source_line else "Source line: (infer from formula)"
    prompt = (
        f"Source formula:\n{source_formula}\n\n"
        f"{source_ctx}\n"
        f"Target line: {target_line} (canonical: {target_canonical_key})\n\n"
        f"Return JSON:\n"
        f'{{"shade":"<closest shade code in {target_line}>","current_level":<1-12>,'
        f'"gray":<0-100>,"texture":"fine|medium|coarse",'
        f'"service_intent":"tone_deposit|lift_deposit|gray_coverage|corrective|fashion",'
        f'"desired_level":<1-12>,"porosity":5,"elasticity":6,"line":"{target_line}",'
        f'"translation_notes":"<explain the tone/level mapping>"}}'
    )
    resp = await _client().chat.completions.create(
        model=settings.translate_model,
        messages=[
            {"role": "system", "content": _TRANSLATE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(resp.choices[0].message.content)
