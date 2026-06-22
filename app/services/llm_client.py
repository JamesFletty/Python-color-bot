"""Single-provider LLM client (OpenAI SDK + configurable base URL)."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from app.config import Settings, get_settings

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
- Aveda Full Spectrum shade notation: O/R=copper/orange-red (strawberry blonde), R/O=red/copper, Y/O=gold/copper, N/N=natural/natural, V/R=violet-red, V/B=ash, B/B=intense ash. "Strawberry blonde" on Aveda = O/R or R/O family at target level; "red violet" = V/R or R/V family at target level.
- Do not choose a plain natural shade when the goal includes warm/cool fashion language (strawberry, copper, red-violet, violet-red, beige, ash).
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
2. Preserve warmth/coolness. Warm source (G, CB, Y/O, R/O, copper, gold, strawberry) → warm target; cool source (B/G, V/B, ash, pearl, violet) → cool target.
   NEVER say source tones are "not required" or "not needed". If no direct target equivalent exists, choose the nearest catalog shade and mark it as nearest-match in translation_notes.
3. Map EACH source component in translation_notes (grams + shade + tone family) and identify the dominant base versus boosters/additives.
4. Redken Shades EQ: G=Gold, N=Natural, CB=Copper Brown (warm), P=Pearl, V=Violet, GI=Gold Iridescent
5. Aveda boosters: Dark Y/O=warm gold/copper, Dark R/O=copper/red, Dark B/G=dark blue/green (COOL — ash/green tone, NOT warm)

Return ONLY valid compact JSON with fields:
shade, current_level, gray, texture, service_intent, desired_level, porosity, elasticity, line, translation_notes"""


class LLMNotConfiguredError(RuntimeError):
    """Raised when LLM routes are called without provider credentials."""


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: AsyncOpenAI | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.llm_api_key)

    def _get_client(self) -> AsyncOpenAI:
        if not self.settings.llm_api_key:
            raise LLMNotConfiguredError(
                "LLM is not configured. Set LLM_API_KEY (and optionally LLM_BASE_URL)."
            )
        if self._client is None:
            kwargs: dict[str, Any] = {"api_key": self.settings.llm_api_key}
            if self.settings.llm_base_url:
                kwargs["base_url"] = self.settings.llm_base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    @staticmethod
    def _completion_text(resp: Any) -> str:
        choices = getattr(resp, "choices", None)
        if not choices:
            raise RuntimeError("LLM provider returned no choices.")
        content = choices[0].message.content
        if content is None:
            raise RuntimeError("LLM provider returned an empty message.")
        return content

    async def parse(self, system: str, user: str) -> str:
        resp = await self._get_client().chat.completions.create(
            model=self.settings.llm_chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return self._completion_text(resp)

    async def translate(self, system: str, user: str) -> str:
        resp = await self._get_client().chat.completions.create(
            model=self.settings.llm_translate_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return self._completion_text(resp)

    async def explain(self, system: str, user: str) -> str:
        resp = await self._get_client().chat.completions.create(
            model=self.settings.llm_chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        return self._completion_text(resp).strip()

    async def parse_formula(
        self,
        *,
        user_input: str,
        color_line: str,
        canonical_key: str,
        catalog_text: str,
        source_summary: str = "",
        deterministic_hint: str = "",
    ) -> dict[str, Any]:
        prompt = (
            f"Product line: {color_line} (canonical: {canonical_key})\n\n"
            f"Stylist input:\n{user_input}\n\n"
            f"{f'Parsed formula hints:\n{source_summary}\n\n' if source_summary else ''}"
            f"CATALOG (shade MUST be from this list):\n{catalog_text}\n\n"
            f"{deterministic_hint}"
            f"Return JSON engine parameters only:\n"
            f'{{"shade":"<from CATALOG>","current_level":<1-12|null>,"gray":<0-100>,'
            f'"texture":"fine|medium|coarse","service_intent":"tone_deposit|lift_deposit|gray_coverage|corrective|fashion",'
            f'"desired_level":<1-12|null>,"porosity":5,"elasticity":6,"line":"{color_line}"}}'
        )
        raw = await self.parse(_PARSE_SYSTEM, prompt)
        return json.loads(raw)

    async def translate_formula(
        self,
        *,
        source_formula: str,
        source_line: str | None,
        target_line: str,
        target_canonical_key: str,
        catalog_text: str,
        source_summary: str = "",
        deterministic_hint: str = "",
    ) -> dict[str, Any]:
        source_ctx = f"Source line: {source_line}" if source_line else "Source line: (infer from formula)"
        prompt = (
            f"Source formula:\n{source_formula}\n\n"
            f"{source_ctx}\n"
            f"{f'Parsed source analysis:\n{source_summary}\n\n' if source_summary else ''}"
            f"Target line: {target_line} (canonical: {target_canonical_key})\n\n"
            f"TARGET CATALOG (pick shade code exactly from this list):\n{catalog_text}\n\n"
            f"{deterministic_hint}"
            f"Return JSON:\n"
            f'{{"shade":"<MUST be from TARGET CATALOG>","current_level":<1-12>,'
            f'"gray":<0-100>,"texture":"fine|medium|coarse",'
            f'"service_intent":"tone_deposit|lift_deposit|gray_coverage|corrective|fashion",'
            f'"desired_level":<1-12>,"porosity":5,"elasticity":6,"line":"{target_line}",'
            f'"translation_notes":"<map EACH source component; preserve warmth/coolness>"}}'
        )
        raw = await self.translate(_TRANSLATE_SYSTEM, prompt)
        return json.loads(raw)

    async def explain_formula(
        self,
        *,
        formula_result: dict[str, Any],
        user_input: str,
        color_line: str,
        mode: str = "formula",
        translation_notes: str | None = None,
    ) -> str:
        if formula_result.get("status") == "error":
            error = formula_result.get("error", "Unknown engine error")
            return (
                f"The formula engine could not complete this recommendation: {error}. "
                f"Re-run after selecting a valid catalog shade."
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
            "Write 2–4 concise sentences for a stylist using ONLY the deterministic formula output. "
            "State the selected shade, developer, mix ratio, processing time when present, and gray/lift rationale when present. "
            "If warnings, assumptions, caution, or blocked status appear, disclose them plainly. "
            "Do NOT mention rule codes, stage numbers, or system names."
        )
        system = (
            "You are a senior colorist auditing deterministic formula output for another stylist. "
            "Be concise, direct, and evidence-bound."
        )
        return await self.explain(system, prompt)
