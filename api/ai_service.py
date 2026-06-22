"""LLM integration for formula parsing and explanation.

Supports Azure OpenAI (preferred when configured), direct OpenAI, xAI Grok, and an
offline mock provider for local testing without API keys.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

import httpx
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
You convert stylist natural language into structured JSON for a deterministic formula engine.
You do NOT recommend products, write salon advice, or invent shade codes.

Your ONLY job: extract engine parameters from stylist input.

Output fields:
- shade: exact shade code from the CATALOG list provided (required)
- current_level: client starting level 1-12 if stated
- desired_level: target level 1-12 if stated
- gray: 0-100 gray percentage if stated
- texture: fine | medium | coarse (default medium)
- service_intent: tone_deposit | lift_deposit | gray_coverage | corrective | fashion
- porosity: 1-10 (default 5)
- elasticity: 1-10 (default 6)
- line: product line name (echo the line given)

Rules:
- shade MUST be copied exactly from the catalog list — never invent codes like 6N on Majirel (use 6.0, 6.46, etc.)
- If input is a multi-shade formula (e.g. 40g 6n + 2g dark y/o + 2g dark r/o + 1g dark b/g), pick the blended equivalent
  shade from catalog that preserves warmth/coolness — do NOT drop warm boosters
- Aveda Dark B/G = dark blue/green = COOL/ASH tone. Never describe it as warm, copper, or gold.
- Aveda Full Spectrum shade notation: O/R=copper/orange-red (strawberry blonde), Y/O=gold, N/N=natural/natural, V/B=ash, B/B=intense ash. "Strawberry blonde" on Aveda = O/R family at target level.
- Redken Shades EQ: G=Gold (NOT Natural), N=Natural, CB=Copper Brown (warm), P=Pearl, V=Violet
- Parse shorthand: 7g=07G gold, 6cb=06CB, 9p=09P pearl, 10v=010V violet
- When the user describes a goal (e.g. "wants level 8 strawberry blonde"), pick the shade at the TARGET level, not the current level.

Return ONLY valid compact JSON. No markdown. No explanation text."""

_TRANSLATE_SYSTEM = """\
You convert a source hair-color formula into structured JSON for a deterministic formula engine.
You do NOT write salon recommendations — only structured translation data.

Your ONLY job: map source formula components to a valid target-line shade code + engine fields.

CRITICAL RULES:
1. shade MUST be copied exactly from TARGET CATALOG — never invent codes (no 9-66, no 6N on Majirel).
   - Majirel: 6.0, 6.46, 6.64 (digit notation)
   - IGORA VIBRANCE: 9-1, 9-65, 6-46 (hyphen notation)
2. Preserve warmth/coolness. Warm source (G, CB, Y/O, R/O, copper, gold) → warm target.
   NEVER say warm tones are "not required" or "not needed".
3. Map EACH source component in translation_notes (grams + shade + tone family).
4. Redken Shades EQ: G=Gold, N=Natural, CB=Copper Brown (warm), P=Pearl, V=Violet, GI=Gold Iridescent
5. Aveda boosters: Dark Y/O=warm gold/copper, Dark R/O=copper/red, Dark B/G=dark blue/green (COOL — ash/green tone, NOT warm)

Return ONLY valid compact JSON with fields:
shade, current_level, gray, texture, service_intent, desired_level, porosity, elasticity, line, translation_notes"""


from api.backend import env, is_production_environment


def _env(name: str, default: str | None = None) -> str | None:
    return env(name, default)


def _normalize_openai_base_url(base_url: str | None) -> str | None:
    """Normalize an OpenAI-compatible base URL.

    Amazon Bedrock's OpenAI-compatible endpoint lives at
    `https://bedrock-runtime.<region>.amazonaws.com/openai/v1`. A common
    misconfiguration is pointing at `/compatible-apis/openai/v1` or `/v1`,
    which Bedrock answers with `UnknownOperationException`. Rewrite those to
    the supported `/openai/v1` path so the integration works regardless of the
    exact value entered in the env var.
    """
    if not base_url:
        return base_url
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(base_url)
    if "bedrock-runtime" in parts.netloc and parts.path.rstrip("/") != "/openai/v1":
        parts = parts._replace(path="/openai/v1")
        return urlunsplit(parts)
    return base_url


def _completion_text(resp: Any) -> str:
    """Extract message content, raising a clear error on an empty/error payload.

    OpenAI-compatible gateways (e.g. Bedrock) may return a 200 with no
    `choices` and an error blob in the body. Accessing `resp.choices[0]`
    then raises an opaque `TypeError: 'NoneType' object is not subscriptable`.
    Surface the actual upstream payload instead.
    """
    choices = getattr(resp, "choices", None)
    if not choices:
        detail = ""
        try:
            detail = resp.model_dump_json()
        except Exception:
            detail = str(resp)
        raise AIConfigurationError(
            "LLM provider returned no choices. Check OPENAI_BASE_URL and that "
            "OPENAI_API_KEY is a valid key for that endpoint. "
            f"Upstream response: {detail[:500]}"
        )
    content = choices[0].message.content
    if content is None:
        raise AIConfigurationError("LLM provider returned an empty message.")
    return content


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
            endpoint=_normalize_openai_base_url(
                _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
            ),
        )
    if not _env("XAI_API_KEY"):
        raise AIConfigurationError("xAI requires XAI_API_KEY.")
    return AISettings(
        provider="xai",
        parse_model=_env("XAI_CHAT_MODEL", "grok-3-mini"),
        translate_model=_env("XAI_TRANSLATE_MODEL", "grok-3"),
        endpoint="https://api.x.ai/v1",
    )


def _is_bedrock_endpoint(endpoint: str | None) -> bool:
    return bool(endpoint and ("amazonaws.com" in endpoint or "api.aws" in endpoint))


def _bedrock_http_client() -> httpx.AsyncClient:
    """Return an httpx client with AWS SigV4 signing for Bedrock endpoints."""
    from httpx_aws_auth import AwsCredentials, AwsSigV4Auth

    access_key = _env("AWS_ACCESS_KEY_ID")
    secret_key = _env("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        raise AIConfigurationError(
            "AWS credentials not found. Ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set."
        )
    region = _env("AWS_REGION") or _env("AWS_DEFAULT_REGION") or "us-east-1"
    credentials = AwsCredentials(
        access_key=access_key,
        secret_key=secret_key,
        session_token=_env("AWS_SESSION_TOKEN"),
    )
    auth = AwsSigV4Auth(credentials=credentials, region=region, service="bedrock")
    return httpx.AsyncClient(auth=auth)


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
        if _is_bedrock_endpoint(settings.endpoint):
            return AsyncOpenAI(
                api_key="bedrock",
                base_url=settings.endpoint,
                http_client=_bedrock_http_client(),
            )
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
    *,
    line_id: str | None = None,
) -> dict[str, Any]:
    """Parse natural-language stylist input into structured engine parameters."""
    from api.ai_translate_support import build_parse_context, ground_structured_result

    context = None
    if line_id:
        context = build_parse_context(user_input, line_id=line_id, color_line=color_line)

    settings = get_ai_settings()
    if settings.provider == "mock":
        from api.ai_mock import mock_parse_formula_request

        parsed = mock_parse_formula_request(user_input, color_line, canonical_key)
        if context and line_id:
            parsed = ground_structured_result(
                parsed, line_id=line_id, product_line=color_line, context=context
            )
        return parsed

    catalog_block = ""
    source_block = ""
    deterministic_hint = ""
    if context:
        if context.get("source_summary"):
            source_block = f"Parsed formula hints:\n{context['source_summary']}\n\n"
        catalog_block = f"CATALOG (shade MUST be from this list):\n{context['catalog_text']}\n\n"
        det = context.get("deterministic_pick")
        if det:
            deterministic_hint = (
                f"Tone-engine suggestion: {det['code']} "
                f"(level {det.get('level')}, tones {det.get('normalized_tones')})\n\n"
            )

    prompt = (
        f"Product line: {color_line} (canonical: {canonical_key})\n\n"
        f"Stylist input:\n{user_input}\n\n"
        f"{source_block}"
        f"{catalog_block}"
        f"{deterministic_hint}"
        f"Return JSON engine parameters only:\n"
        f'{{"shade":"<from CATALOG>","current_level":<1-12|null>,"gray":<0-100>,'
        f'"texture":"fine|medium|coarse","service_intent":"tone_deposit|lift_deposit|gray_coverage|corrective|fashion",'
        f'"desired_level":<1-12|null>,"porosity":5,"elasticity":6,"line":"{color_line}"}}'
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
    parsed = json.loads(_completion_text(resp))
    if context and line_id:
        parsed = ground_structured_result(
            parsed, line_id=line_id, product_line=color_line, context=context
        )
    return parsed


async def explain_formula(
    formula_result: dict[str, Any],
    user_input: str,
    color_line: str,
    mode: str = "formula",
    translation_notes: str | None = None,
) -> str:
    """Generate a concise professional explanation of the formula."""
    if formula_result.get("status") == "error":
        error = formula_result.get("error", "Unknown engine error")
        grounded = translation_notes or ""
        return (
            f"The deterministic formula engine could not complete this recommendation: {error}. "
            f"The AI translation suggested a shade that is not in the {color_line} catalog, or the "
            f"database is missing that shade. "
            f"{'Parsed source: ' + grounded + '. ' if grounded else ''}"
            f"Expand 'raw engine output' below for details. Re-run after selecting a valid catalog shade."
        )

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
        f"Formula engine output:\n"
        f"{json.dumps(formula_result, indent=2)}\n\n"
        "Write 1–2 sentences for a stylist. State: what shade and developer to use and why it achieves the goal. "
        "Do NOT mention rule codes, stage numbers, engine internals, or system names. "
        "Do NOT tell the stylist to 'account for' warmth or anything else — the formula already handles it. "
        "Just state the result plainly. Professional, direct, no hedging."
    )
    resp = await _client().chat.completions.create(
        model=settings.parse_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior colorist giving a brief formula note to another stylist. "
                    "Be concise and direct. Never mention internal rule codes, stage numbers, or engine details. "
                    "The formula is already correct — do not add caveats or application warnings."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return _completion_text(resp).strip()


async def translate_formula(
    source_formula: str,
    source_line: str | None,
    target_line: str,
    target_canonical_key: str,
    *,
    target_line_id: str | None = None,
    source_canonical_key: str | None = None,
) -> dict[str, Any]:
    """Translate a formula from one color line to another."""
    from api.ai_translate_support import build_translation_context, ground_translation_result
    from api.catalog import resolve_canonical_key

    effective_source_key = source_canonical_key
    if not effective_source_key:
        effective_source_key = resolve_canonical_key(source_line)

    context = None
    if target_line_id:
        context = build_translation_context(
            source_formula,
            source_line,
            target_line_id=target_line_id,
            target_line=target_line,
            source_canonical_key=effective_source_key,
            target_canonical_key=target_canonical_key,
        )

    settings = get_ai_settings()
    if settings.provider == "mock":
        from api.ai_mock import mock_translate_formula

        parsed = mock_translate_formula(
            source_formula,
            source_line,
            target_line,
            target_canonical_key,
        )
        if context:
            parsed["translation_notes"] = (
                f"{context['source_summary']}. {parsed.get('translation_notes', '')}"
            ).strip()
            parsed = ground_translation_result(
                parsed,
                line_id=target_line_id or "",
                product_line=target_line,
                context=context,
            )
        return parsed

    source_ctx = f"Source line: {source_line}" if source_line else "Source line: (infer from formula)"
    catalog_block = ""
    source_block = ""
    deterministic_hint = ""
    if context:
        source_block = f"Parsed source analysis:\n{context['source_summary']}\n\n"
        catalog_block = f"TARGET CATALOG (pick shade code exactly from this list):\n{context['catalog_text']}\n\n"
        det = context.get("deterministic_pick")
        if det:
            hint = (
                f"Suggested catalog match from cross-line map/tone engine: {det['code']} "
                f"(level {det.get('level')}, tones {det.get('normalized_tones')})"
            )
            if det.get("conversion_notes"):
                hint += f"\nComponent mapping: {det['conversion_notes']}"
            deterministic_hint = hint + "\n\n"

    prompt = (
        f"Source formula:\n{source_formula}\n\n"
        f"{source_ctx}\n"
        f"{source_block}"
        f"Target line: {target_line} (canonical: {target_canonical_key})\n\n"
        f"{catalog_block}"
        f"{deterministic_hint}"
        f"Return JSON:\n"
        f'{{"shade":"<MUST be from TARGET CATALOG>","current_level":<1-12>,'
        f'"gray":<0-100>,"texture":"fine|medium|coarse",'
        f'"service_intent":"tone_deposit|lift_deposit|gray_coverage|corrective|fashion",'
        f'"desired_level":<1-12>,"porosity":5,"elasticity":6,"line":"{target_line}",'
        f'"translation_notes":"<map EACH source component; preserve warmth/coolness>"}}'
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
    parsed = json.loads(_completion_text(resp))
    if context and target_line_id:
        parsed = ground_translation_result(
            parsed,
            line_id=target_line_id,
            product_line=target_line,
            context=context,
        )
    return parsed
