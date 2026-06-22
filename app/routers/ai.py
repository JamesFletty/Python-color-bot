"""AI routes — parse, translate, explain."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.ai import (
    AIExplainRequest,
    AIParseRequest,
    AITranslateRequest,
    AITranslateResponse,
    ExplainResponse,
    ParsedRequest,
)
from app.schemas.formula import FormulaRequest
from app.services.ai_context import (
    build_parse_context,
    build_translation_context,
    deterministic_parse,
    ground_parsed_result,
)
from app.services.formula_engine import ShadeNotFoundError, build_formula
from app.services.llm_client import LLMClient, LLMNotConfiguredError

router = APIRouter(prefix="/ai", tags=["ai"])


def _parsed_to_formula_request(parsed: dict[str, Any], *, line_hint: str | None = None) -> FormulaRequest:
    gray = parsed.get("gray_percent", parsed.get("gray", 0))
    return FormulaRequest(
        shade=str(parsed.get("shade") or line_hint or ""),
        line_hint=parsed.get("line") or line_hint,
        current_level=parsed.get("current_level"),
        desired_level=parsed.get("desired_level"),
        gray_percent=float(gray or 0),
        porosity=int(parsed.get("porosity", 5)),
        elasticity=int(parsed.get("elasticity", 6)),
        texture=parsed.get("texture", "medium"),
        service_intent=parsed.get("service_intent", "tone_deposit"),
    )


def _to_parsed_request(data: dict[str, Any], *, parse_source: str) -> ParsedRequest:
    gray = data.get("gray_percent", data.get("gray", 0))
    return ParsedRequest(
        shade=str(data.get("shade", "")),
        current_level=data.get("current_level"),
        desired_level=data.get("desired_level"),
        gray_percent=float(gray or 0),
        porosity=int(data.get("porosity", 5)),
        elasticity=int(data.get("elasticity", 6)),
        texture=data.get("texture", "medium"),
        service_intent=data.get("service_intent", "tone_deposit"),
        line=data.get("line"),
        translation_notes=data.get("translation_notes"),
        parse_source=parse_source,  # type: ignore[arg-type]
    )


@router.post("/parse", response_model=ParsedRequest)
async def ai_parse(body: AIParseRequest, db: Session = Depends(get_db)) -> ParsedRequest:
    llm = LLMClient()
    parse_source = "deterministic"

    if llm.is_configured:
        try:
            context = build_parse_context(
                db,
                body.user_input,
                line_id=body.line_id,
                color_line=body.color_line,
            )
            det = context.get("deterministic_pick") or {}
            det_hint = ""
            if det:
                det_hint = (
                    f"Tone-engine suggestion: {det.get('shade_code')} "
                    f"(level {det.get('level')}, tones {det.get('normalized_tones')})\n\n"
                )
            parsed = await llm.parse_formula(
                user_input=body.user_input,
                color_line=body.color_line,
                canonical_key=body.canonical_key,
                catalog_text=context["catalog_text"],
                source_summary=context.get("source_summary", ""),
                deterministic_hint=det_hint,
            )
            parsed = ground_parsed_result(
                db, parsed, line_id=body.line_id, color_line=body.color_line
            )
            parse_source = "llm"
            return _to_parsed_request(parsed, parse_source=parse_source)
        except (LLMNotConfiguredError, RuntimeError):
            pass
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AI parsing failed: {exc}") from exc

    parsed = deterministic_parse(
        db,
        body.user_input,
        color_line=body.color_line,
        line_id=body.line_id,
    )
    return _to_parsed_request(parsed, parse_source=parse_source)


@router.post("/translate", response_model=AITranslateResponse)
async def ai_translate(
    body: AITranslateRequest,
    db: Session = Depends(get_db),
) -> AITranslateResponse:
    llm = LLMClient()
    parse_source = "deterministic"
    parsed: dict[str, Any]

    if llm.is_configured:
        try:
            context = build_translation_context(
                db,
                body.source_formula,
                source_canonical_key=body.source_canonical_key,
                target_line_id=body.target_line_id,
                target_line=body.target_line,
                target_canonical_key=body.target_canonical_key,
            )
            det = context.get("deterministic_pick") or {}
            det_hint = ""
            if det:
                det_hint = (
                    f"Suggested catalog match: {det.get('code') or det.get('shade_code')} "
                    f"(level {det.get('level')}, tones {det.get('normalized_tones')})\n\n"
                )
            parsed = await llm.translate_formula(
                source_formula=body.source_formula,
                source_line=body.source_line,
                target_line=body.target_line,
                target_canonical_key=body.target_canonical_key,
                catalog_text=context["catalog_text"],
                source_summary=context.get("source_summary", ""),
                deterministic_hint=det_hint,
            )
            parsed = ground_parsed_result(
                db,
                parsed,
                line_id=body.target_line_id,
                color_line=body.target_line,
            )
            parse_source = "llm"
        except LLMNotConfiguredError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AI translation failed: {exc}") from exc
    else:
        raise HTTPException(
            status_code=503,
            detail="LLM is not configured. Set LLM_API_KEY for translation.",
        )

    translation_notes = parsed.pop("translation_notes", None)
    try:
        formula = build_formula(
            _parsed_to_formula_request(parsed, line_hint=body.target_line),
            db,
        )
    except ShadeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return AITranslateResponse(
        **formula.model_dump(),
        structured_request=parsed,
        translation_notes=translation_notes,
        parse_source=parse_source,  # type: ignore[arg-type]
    )


@router.post("/explain", response_model=ExplainResponse)
async def ai_explain(body: AIExplainRequest) -> ExplainResponse:
    llm = LLMClient()
    if not llm.is_configured:
        raise HTTPException(
            status_code=503,
            detail="LLM is not configured. Set LLM_API_KEY for explanations.",
        )
    try:
        summary = await llm.explain_formula(
            formula_result=body.formula_result,
            user_input=body.user_input,
            color_line=body.color_line,
            mode=body.mode,
            translation_notes=body.translation_notes,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI explanation failed: {exc}") from exc
    return ExplainResponse(summary=summary)
