#!/usr/bin/env python3
"""Emit all Stage 13 formulation-rules package JSON artifacts and integration notes."""

from __future__ import annotations

import json
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
GENERATED = "2026-06-15"

A_FORMULATION_ONTOLOGY: dict = {
    "stage": 13,
    "artifact": "formulation_ontology",
    "generated": GENERATED,
    "completion_status": "complete",
    "entities": [
        {
            "entity_id": "consultation",
            "description": "Client session capturing hair history, goals, and safety gates.",
            "fields": [
                "consultation_id",
                "client_id",
                "patch_test_status",
                "patch_test_date",
                "allergy_notes",
            ],
        },
        {
            "entity_id": "hair_state",
            "description": "Observed and declared hair condition at service time.",
            "fields": [
                "natural_level",
                "existing_level",
                "existing_artificial_color",
                "porosity",
                "elasticity",
                "gray_percentage",
                "texture",
                "pre_lightened",
                "previous_direct_dye",
            ],
        },
        {
            "entity_id": "service_intent",
            "description": "High-level service classification driving workflow and rule templates.",
            "fields": ["service_intent", "desired_result", "desired_level", "desired_tone"],
        },
        {
            "entity_id": "formula_step",
            "description": "Ordered application step with shade, developer, ratio, and timing.",
            "fields": [
                "step_order",
                "zone",
                "shade_code",
                "sub_range_name",
                "developer_volume",
                "mixing_ratio",
                "processing_time_minutes",
                "special_instructions",
            ],
        },
        {
            "entity_id": "formulation_rule",
            "description": "Deterministic if/then rule with scope tier universal, brand, or line.",
            "fields": [
                "rule_id",
                "rule_name",
                "rule_priority",
                "rule_condition",
                "rule_action",
                "rule_category",
                "scope_level",
            ],
        },
        {
            "entity_id": "risk_assessment",
            "description": "Draft risk row with probability, severity, and mitigation.",
            "fields": ["risk_type", "probability", "severity", "contributing_factors", "mitigation"],
        },
    ],
    "enums": {
        "service_intent": [
            "tone_deposit",
            "gray_coverage",
            "lift_and_tone",
            "correction",
            "gloss_refresh",
        ],
        "recommendation_status": ["ok", "caution", "blocked", "requires_consultation"],
        "formula_zone": ["root", "mid", "end", "all"],
        "hair_texture": ["fine", "medium", "coarse"],
        "porosity_scale": {
            "min": 1,
            "max": 10,
            "labels": {
                "1-3": "low",
                "4-6": "medium",
                "7-10": "high",
            },
        },
        "patch_test_status": ["not_required", "pending", "passed", "failed", "waived_documented"],
        "evidence_status": [
            "manufacturer_stated",
            "educator_reported",
            "inferred",
            "conflicting",
            "missing",
        ],
        "rule_scope_level": ["universal", "brand", "line"],
    },
    "developer_profiles": [
        {
            "profile_id": "DEV_10VOL",
            "volume": 10,
            "percent_peroxide": 3.0,
            "typical_use": "Deposit-only, gloss refresh, same-level tone.",
        },
        {
            "profile_id": "DEV_20VOL",
            "volume": 20,
            "percent_peroxide": 6.0,
            "typical_use": "1-2 levels lift, gray coverage on resistant hair.",
        },
        {
            "profile_id": "DEV_30VOL",
            "volume": 30,
            "percent_peroxide": 9.0,
            "typical_use": "2-3 levels lift on virgin or pre-lightened hair.",
        },
        {
            "profile_id": "DEV_40VOL",
            "volume": 40,
            "percent_peroxide": 12.0,
            "typical_use": "High lift; requires consultation and strand test.",
        },
        {
            "profile_id": "DEV_ACIDIC_DEMI",
            "volume": None,
            "percent_peroxide": 1.9,
            "typical_use": "Acidic demi developers (SEQ, Color Touch) — no lift.",
        },
        {
            "profile_id": "DEV_NONE",
            "volume": None,
            "percent_peroxide": 0.0,
            "typical_use": "Direct dye / semi-permanent — no developer.",
        },
    ],
    "underlying_pigment_default_map": [
        {"level": 1, "underlying_pigment": "Blue-violet", "exposure_stage": "Darkest"},
        {"level": 2, "underlying_pigment": "Blue-violet", "exposure_stage": "Very dark"},
        {"level": 3, "underlying_pigment": "Blue-violet", "exposure_stage": "Dark"},
        {"level": 4, "underlying_pigment": "Red-violet", "exposure_stage": "Medium dark"},
        {"level": 5, "underlying_pigment": "Red-orange", "exposure_stage": "Medium"},
        {"level": 6, "underlying_pigment": "Orange", "exposure_stage": "Mid lift"},
        {"level": 7, "underlying_pigment": "Orange-yellow", "exposure_stage": "Lifted"},
        {"level": 8, "underlying_pigment": "Yellow-orange", "exposure_stage": "Light"},
        {"level": 9, "underlying_pigment": "Yellow", "exposure_stage": "High lift"},
        {"level": 10, "underlying_pigment": "Pale yellow", "exposure_stage": "Pale stage"},
    ],
    "complementary_color_pairs": [
        {"warm_tone": "orange", "neutralizing_tone": "blue", "wheel_position": "direct complement"},
        {"warm_tone": "yellow", "neutralizing_tone": "violet", "wheel_position": "direct complement"},
        {"warm_tone": "red", "neutralizing_tone": "green", "wheel_position": "direct complement"},
        {"warm_tone": "red-orange", "neutralizing_tone": "blue-green", "wheel_position": "split complement"},
        {"warm_tone": "gold", "neutralizing_tone": "violet-ash", "wheel_position": "hair-color practice"},
        {"warm_tone": "copper", "neutralizing_tone": "ash-blue", "wheel_position": "hair-color practice"},
        {"warm_tone": "brass", "neutralizing_tone": "ash-violet", "wheel_position": "hair-color practice"},
    ],
}

B_UNIVERSAL_RULE_LIBRARY: dict = {
    "stage": 13,
    "artifact": "universal_rule_library",
    "generated": GENERATED,
    "universal_rules": [
        {
            "rule_id": "U001",
            "rule_name": "patch_test_fail_blocks_service",
            "rule_priority": 10,
            "rule_category": "safety",
            "evidence_status": "educator_reported",
            "rule_condition": {
                "all_of": [{"field": "patch_test_status", "op": "=", "value": "failed"}]
            },
            "rule_action": {
                "set_recommendation_status": "blocked",
                "block_reason": "Patch test failed; do not proceed with color service.",
            },
        },
        {
            "rule_id": "U002",
            "rule_name": "gray_coverage_high_natural_mix",
            "rule_priority": 50,
            "rule_category": "gray_coverage",
            "evidence_status": "educator_reported",
            "rule_condition": {
                "all_of": [
                    {"field": "gray_percentage", "op": ">", "value": 50},
                    {"field": "natural_level", "op": "<=", "value": 6},
                ]
            },
            "rule_action": {
                "set_developer_volume": 20,
                "require_natural_shade_mix": True,
                "natural_shade_ratio": 0.5,
            },
        },
        {
            "rule_id": "U003",
            "rule_name": "high_porosity_reduce_developer_time",
            "rule_priority": 60,
            "rule_category": "porosity",
            "evidence_status": "educator_reported",
            "rule_condition": {"any_of": [{"field": "porosity", "op": ">", "value": 7}]},
            "rule_action": {
                "adjust_developer_volume_delta": -10,
                "adjust_processing_time_minutes": -5,
            },
        },
        {
            "rule_id": "U004",
            "rule_name": "lift_over_four_prelighten_consult",
            "rule_priority": 40,
            "rule_category": "lift",
            "evidence_status": "educator_reported",
            "rule_condition": {"all_of": [{"field": "lift_levels", "op": ">", "value": 4}]},
            "rule_action": {
                "trigger_workflow": "pre_lightening_consultation",
                "risk_modifier": {"unrealistic_expectation": 0.3},
            },
        },
        {
            "rule_id": "U005",
            "rule_name": "artificial_color_lighter_correction",
            "rule_priority": 45,
            "rule_category": "correction",
            "evidence_status": "inferred",
            "rule_condition": {
                "all_of": [
                    {"field": "existing_artificial_color", "op": "exists", "value": True},
                    {"field": "desired_level", "op": ">", "value": "existing_level"},
                ]
            },
            "rule_action": {
                "trigger_workflow": "color_correction",
                "risk_modifier": {"overlap": 0.25},
            },
        },
        {
            "rule_id": "U006",
            "rule_name": "color_does_not_lift_color",
            "rule_priority": 35,
            "rule_category": "color_science",
            "evidence_status": "educator_reported",
            "rule_condition": {
                "all_of": [
                    {"field": "existing_artificial_color", "op": "exists", "value": True},
                    {"field": "lift_levels", "op": ">", "value": 0},
                    {"field": "pre_lightened", "op": "!=", "value": True},
                ]
            },
            "rule_action": {
                "set_recommendation_status": "requires_consultation",
                "warning": "Permanent color cannot reliably lift artificial color; pre-lighten or corrective path required.",
                "trigger_workflow": "color_correction",
            },
        },
        {
            "rule_id": "U007",
            "rule_name": "fine_texture_high_lift_breakage_risk",
            "rule_priority": 70,
            "rule_category": "lift",
            "evidence_status": "educator_reported",
            "rule_condition": {
                "all_of": [
                    {"field": "texture", "op": "=", "value": "fine"},
                    {"field": "lift_levels", "op": ">=", "value": 3},
                ]
            },
            "rule_action": {"increase_risk_score": {"breakage": 0.35}},
        },
        {
            "rule_id": "U008",
            "rule_name": "underlying_pigment_neutralization_warning",
            "rule_priority": 55,
            "rule_category": "color_science",
            "evidence_status": "educator_reported",
            "rule_condition": {"all_of": [{"field": "lift_levels", "op": ">=", "value": 2}]},
            "rule_action": {
                "warning": "Lift exposes underlying warm pigment; select complementary neutralizing tone.",
                "lookup": "underlying_pigment_default_map",
            },
        },
        {
            "rule_id": "U009",
            "rule_name": "direct_dye_no_developer",
            "rule_priority": 25,
            "rule_category": "product_type",
            "evidence_status": "manufacturer_stated",
            "rule_condition": {
                "all_of": [{"field": "line_category", "op": "=", "value": "direct_dye"}]
            },
            "rule_action": {
                "set_developer_volume": None,
                "mixing_ratio": "direct_application",
                "warning": "Direct dye / semi-permanent — no developer mixed.",
            },
        },
        {
            "rule_id": "U010",
            "rule_name": "refresh_restricted_high_porosity",
            "rule_priority": 65,
            "rule_category": "porosity",
            "evidence_status": "educator_reported",
            "rule_condition": {
                "all_of": [
                    {"field": "service_intent", "op": "=", "value": "gloss_refresh"},
                    {"field": "porosity", "op": ">", "value": 7},
                ]
            },
            "rule_action": {
                "set_recommendation_status": "caution",
                "adjust_processing_time_minutes": -5,
                "warning": "High porosity — shorten refresh time; monitor absorption.",
            },
        },
        {
            "rule_id": "U011",
            "rule_name": "overlap_application_risk",
            "rule_priority": 75,
            "rule_category": "application",
            "evidence_status": "educator_reported",
            "rule_condition": {
                "all_of": [
                    {"field": "service_intent", "op": "in", "value": ["gray_coverage", "lift_and_tone"]},
                    {"field": "existing_artificial_color", "op": "exists", "value": True},
                ]
            },
            "rule_action": {"risk_modifier": {"overlap": 0.2}},
        },
        {
            "rule_id": "U012",
            "rule_name": "universal_default_developer",
            "rule_priority": 200,
            "rule_category": "developer",
            "evidence_status": "inferred",
            "rule_condition": {
                "all_of": [{"field": "service_intent", "op": "exists", "value": True}]
            },
            "rule_action": {"set_developer_volume": 10},
        },
    ],
}

C_SERVICE_WORKFLOWS: dict = {
    "stage": 13,
    "artifact": "service_workflows",
    "generated": GENERATED,
    "service_workflows": [
        {
            "workflow_id": "WF_virgin_permanent",
            "name": "Virgin permanent color",
            "service_intent": "lift_and_tone",
            "steps": [
                "Assess natural level and desired lift.",
                "Select permanent line shade + developer per lift delta.",
                "Apply root-to-ends or zone-specific per manufacturer guidance.",
            ],
            "default_zones": ["root", "mid", "end"],
            "applicable_line_categories": ["permanent"],
        },
        {
            "workflow_id": "WF_virgin_demipermanent",
            "name": "Virgin demi-permanent deposit",
            "service_intent": "tone_deposit",
            "steps": [
                "Confirm no lift required.",
                "Select demi shade at or darker than natural level.",
                "Process per line technical rules.",
            ],
            "default_zones": ["all"],
            "applicable_line_categories": ["demi"],
        },
        {
            "workflow_id": "WF_retouch_root",
            "name": "Root retouch",
            "service_intent": "gray_coverage",
            "steps": [
                "Apply permanent color to new growth at root zone.",
                "Feather mid-shaft if overlap risk is low.",
                "Refresh ends only when porosity and condition allow.",
            ],
            "default_zones": ["root"],
            "applicable_line_categories": ["permanent"],
        },
        {
            "workflow_id": "WF_retouch_with_refresh",
            "name": "Retouch with ends refresh",
            "service_intent": "gloss_refresh",
            "steps": [
                "Permanent or demi at root per coverage need.",
                "Demi/gloss refresh on mid-lengths and ends.",
                "Stagger processing times when porosity differs by zone.",
            ],
            "default_zones": ["root", "mid", "end"],
            "applicable_line_categories": ["permanent", "demi"],
        },
        {
            "workflow_id": "WF_gray_coverage",
            "name": "Gray coverage blend or full cover",
            "service_intent": "gray_coverage",
            "steps": [
                "Classify gray percentage and resistant vs porous.",
                "Add natural-series mix when gray > 50%.",
                "Select developer strength per line override rules.",
            ],
            "default_zones": ["root", "mid", "end"],
            "applicable_line_categories": ["permanent", "demi"],
        },
        {
            "workflow_id": "WF_lift_and_tone",
            "name": "Lift and tone (single process)",
            "service_intent": "lift_and_tone",
            "steps": [
                "Calculate lift delta from natural or existing level.",
                "Apply lift-appropriate developer and processing time.",
                "Neutralize exposed underlying pigment with selected tone.",
            ],
            "default_zones": ["all"],
            "applicable_line_categories": ["permanent"],
        },
        {
            "workflow_id": "WF_prelighten_then_tone",
            "name": "Pre-lighten then tone",
            "service_intent": "lift_and_tone",
            "steps": [
                "Consult when lift > 4 levels or on previously colored hair.",
                "Lighten to target underlying stage with lightener.",
                "Tone with demi or permanent per line capability.",
            ],
            "default_zones": ["all"],
            "applicable_line_categories": ["permanent", "demi", "lightener"],
        },
        {
            "workflow_id": "WF_color_correction",
            "name": "Color correction",
            "service_intent": "correction",
            "steps": [
                "Document existing artificial color and history.",
                "Select removal, fill, or repigmentation strategy.",
                "No auto-formula; stylist-led multi-appointment plan.",
            ],
            "default_zones": [],
            "applicable_line_categories": ["permanent", "demi", "lightener"],
        },
        {
            "workflow_id": "WF_corrective_safe",
            "name": "Corrective safe path",
            "service_intent": "correction",
            "steps": [
                "Strand test mandatory.",
                "Lowest-risk demi or direct deposit to stabilize.",
                "Escalate to full correction only after assessment.",
            ],
            "default_zones": ["all"],
            "applicable_line_categories": ["demi", "direct_dye"],
        },
    ],
}

D_BRAND_LINE_OVERRIDES: dict = {
    "stage": 13,
    "artifact": "brand_line_overrides",
    "generated": GENERATED,
    "brand_line_overrides": [
        {
            "canonical_key": "Matrix::SoColor::US",
            "brand_name": "Matrix",
            "product_line_name": "SoColor",
            "requires_stage12_inventory_addition": False,
            "override_rules": [
                {
                    "rule_id": "M_SOCOLOR_001",
                    "rule_name": "matrix_socolor_resistant_gray_20vol",
                    "rule_priority": 55,
                    "rule_category": "gray_coverage",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "gray_percentage", "op": ">=", "value": 50}]
                    },
                    "rule_action": {
                        "set_developer_volume": 30,
                        "add_step": {"zone": "root", "processing_time_adjustment": "+10min"},
                    },
                },
                {
                    "rule_id": "M_SOCOLOR_002",
                    "rule_name": "matrix_socolor_hd_not_mixable",
                    "rule_priority": 30,
                    "rule_category": "intermixing",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "selected_sub_ranges", "op": "contains", "value": "HD"}]
                    },
                    "rule_action": {
                        "set_recommendation_status": "blocked",
                        "block_reason": "HD Series not mixable with other SoColor shades.",
                    },
                },
            ],
        },
        {
            "canonical_key": "Matrix::SoColor Sync::US",
            "brand_name": "Matrix",
            "product_line_name": "SoColor Sync",
            "requires_stage12_inventory_addition": False,
            "override_rules": [
                {
                    "rule_id": "M_SYNC_001",
                    "rule_name": "sync_gray_blend_not_full_cover",
                    "rule_priority": 50,
                    "rule_category": "gray_coverage",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "gray_percentage", "op": ">=", "value": 80}]
                    },
                    "rule_action": {
                        "set_recommendation_status": "blocked",
                        "block_reason": "SoColor Sync is for gray blending; full cover at 80%+ gray prohibited.",
                    },
                },
                {
                    "rule_id": "M_SYNC_002",
                    "rule_name": "sync_pre_paired_with_socolor",
                    "rule_priority": 80,
                    "rule_category": "application",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "service_intent", "op": "=", "value": "gloss_refresh"}]
                    },
                    "rule_action": {
                        "warning": "Sync is pre-paired with SoColor permanent for root-to-ends services."
                    },
                },
            ],
        },
        {
            "canonical_key": "Matrix::Coil Color::US",
            "brand_name": "Matrix",
            "product_line_name": "Coil Color",
            "requires_stage12_inventory_addition": True,
            "override_rules": [
                {
                    "rule_id": "M_COIL_001",
                    "rule_name": "coil_gray_natural_ratio",
                    "rule_priority": 45,
                    "rule_category": "gray_coverage",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "gray_percentage", "op": ">", "value": 30}]
                    },
                    "rule_action": {
                        "require_natural_shade_mix": True,
                        "natural_shade_ratio": 0.6,
                        "warning": "Coil Color gray coverage requires elevated natural-series ratio.",
                    },
                },
            ],
        },
        {
            "canonical_key": "Matrix::Super Sync::US",
            "brand_name": "Matrix",
            "product_line_name": "Super Sync",
            "requires_stage12_inventory_addition": True,
            "override_rules": [
                {
                    "rule_id": "M_SSYNC_001",
                    "rule_name": "supersync_tint_back",
                    "rule_priority": 50,
                    "rule_category": "application",
                    "evidence_status": "inferred",
                    "rule_condition": {
                        "all_of": [
                            {"field": "service_intent", "op": "=", "value": "tone_deposit"},
                            {"field": "pre_lightened", "op": "=", "value": True},
                        ]
                    },
                    "rule_action": {
                        "trigger_workflow": "WF_retouch_with_refresh",
                        "warning": "Super Sync tint-back on pre-lightened hair — monitor porosity.",
                    },
                },
                {
                    "rule_id": "M_SSYNC_002",
                    "rule_name": "supersync_hd_mix_block",
                    "rule_priority": 30,
                    "rule_category": "intermixing",
                    "evidence_status": "inferred",
                    "rule_condition": {
                        "all_of": [{"field": "selected_sub_ranges", "op": "contains", "value": "HD"}]
                    },
                    "rule_action": {
                        "set_recommendation_status": "blocked",
                        "block_reason": "Super Sync HD shades cannot be intermixed with standard Sync shades.",
                    },
                },
            ],
        },
        {
            "canonical_key": "Matrix::Tonal Control::US",
            "brand_name": "Matrix",
            "product_line_name": "Tonal Control Pre-Bonded",
            "requires_stage12_inventory_addition": True,
            "override_rules": [
                {
                    "rule_id": "M_TC_001",
                    "rule_name": "tonal_control_prelightened_only",
                    "rule_priority": 40,
                    "rule_category": "application",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "pre_lightened", "op": "!=", "value": True}]
                    },
                    "rule_action": {
                        "set_recommendation_status": "blocked",
                        "block_reason": "Tonal Control is for pre-lightened or highlighted hair only.",
                    },
                },
            ],
        },
        {
            "canonical_key": "Redken::Color Gels Lacquers::US",
            "brand_name": "Redken",
            "product_line_name": "Color Gels Lacquers",
            "requires_stage12_inventory_addition": False,
            "override_rules": [
                {
                    "rule_id": "R_CGL_001",
                    "rule_name": "cgl_resistant_gray_30vol",
                    "rule_priority": 55,
                    "rule_category": "gray_coverage",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "gray_percentage", "op": ">=", "value": 50}]
                    },
                    "rule_action": {
                        "set_developer_volume": 30,
                        "require_natural_shade_mix": True,
                        "natural_shade_ratio": 0.5,
                    },
                },
            ],
        },
        {
            "canonical_key": "Redken::Shades EQ Gloss::US",
            "brand_name": "Redken",
            "product_line_name": "Shades EQ Gloss",
            "requires_stage12_inventory_addition": False,
            "override_rules": [
                {
                    "rule_id": "R_SEQ_001",
                    "rule_name": "seq_no_lift_deposit",
                    "rule_priority": 35,
                    "rule_category": "lift",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "lift_levels", "op": ">", "value": 0}]
                    },
                    "rule_action": {
                        "set_recommendation_status": "blocked",
                        "block_reason": "Shades EQ is no-lift demi-gloss; cannot lighten natural pigment.",
                    },
                },
                {
                    "rule_id": "R_SEQ_002",
                    "rule_name": "seq_gray_blend_processing",
                    "rule_priority": 60,
                    "rule_category": "gray_coverage",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "gray_percentage", "op": ">", "value": 0}]
                    },
                    "rule_action": {
                        "adjust_processing_time_minutes": 5,
                        "warning": "Gray blending may require capped heat processing per chart.",
                    },
                },
            ],
        },
        {
            "canonical_key": "Wella Professionals::Color Touch::US",
            "brand_name": "Wella Professionals",
            "product_line_name": "Color Touch",
            "requires_stage12_inventory_addition": False,
            "override_rules": [
                {
                    "rule_id": "W_CT_001",
                    "rule_name": "colortouch_soft_blend",
                    "rule_priority": 65,
                    "rule_category": "gray_coverage",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [
                            {"field": "gray_percentage", "op": ">", "value": 0},
                            {"field": "gray_percentage", "op": "<", "value": 50},
                        ]
                    },
                    "rule_action": {
                        "warning": "Color Touch soft blend path for low gray; not full coverage.",
                        "set_developer_volume": 6,
                    },
                },
            ],
        },
        {
            "canonical_key": "Wella Professionals::Koleston Perfect::US",
            "brand_name": "Wella Professionals",
            "product_line_name": "Koleston Perfect",
            "requires_stage12_inventory_addition": False,
            "override_rules": [
                {
                    "rule_id": "W_KP_001",
                    "rule_name": "koleston_lift_developer_matrix",
                    "rule_priority": 50,
                    "rule_category": "lift",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "lift_levels", "op": "=", "value": 1}]
                    },
                    "rule_action": {"set_developer_volume": 20},
                },
                {
                    "rule_id": "W_KP_002",
                    "rule_name": "koleston_high_lift_consult",
                    "rule_priority": 40,
                    "rule_category": "lift",
                    "evidence_status": "manufacturer_stated",
                    "rule_condition": {
                        "all_of": [{"field": "lift_levels", "op": ">=", "value": 3}]
                    },
                    "rule_action": {
                        "trigger_workflow": "pre_lightening_consultation",
                        "set_developer_volume": 30,
                    },
                },
            ],
        },
    ],
}

E_DECISION_ORDER: dict = {
    "stage": 13,
    "artifact": "decision_order",
    "generated": GENERATED,
    "evaluation_phases": [
        {
            "phase": 1,
            "name": "safety_gates",
            "description": "Hard stops before any formula assembly.",
            "rule_sources": ["universal_rules"],
            "filter": {"rule_category": ["safety"]},
            "stop_on": ["blocked"],
        },
        {
            "phase": 2,
            "name": "service_workflow_selection",
            "description": "Map service_intent and hair state to workflow template.",
            "rule_sources": ["service_workflows"],
            "inputs": ["service_intent", "line_category", "pre_lightened"],
        },
        {
            "phase": 3,
            "name": "universal_rules",
            "description": "Apply universal formulation rules in ascending rule_priority.",
            "rule_sources": ["universal_rules"],
            "scope_level": "universal",
            "sort_by": ["rule_priority"],
        },
        {
            "phase": 4,
            "name": "line_overrides",
            "description": "Apply active brand_line_overrides for canonical_key.",
            "rule_sources": ["brand_line_overrides"],
            "scope_level": "line",
            "sort_by": ["rule_priority"],
            "activation": "active_override_groups()",
        },
        {
            "phase": 5,
            "name": "intermixing_and_color_science",
            "description": "Check shade_intermixing_rule and universal_color_science.",
            "rule_sources": ["stage12_intermixing", "underlying_pigment_default_map"],
        },
        {
            "phase": 6,
            "name": "line_technical_defaults",
            "description": "Fill developer, ratio, and timing from Stage 12 line technical records.",
            "rule_sources": ["stage12_line_technical"],
            "only_fill_gaps": True,
        },
        {
            "phase": 7,
            "name": "recommendation_status",
            "description": "Derive final status from accumulated actions, risks, and blocks.",
            "outputs": ["recommendation_status", "suggested_formula", "warnings"],
        },
    ],
    "conflict_resolution": {
        "scalar_fields": "later phase and higher scope tier wins",
        "risk_modifiers": "accumulate (sum per risk key)",
        "workflows": "append; color_correction suppresses auto-formula",
        "blocks": "any blocked status is terminal",
    },
}

F_VALIDATION_CASES: dict = {
    "stage": 13,
    "artifact": "validation_cases",
    "generated": GENERATED,
    "validation_cases": [
        {
            "case_id": "VC001_safety_patch_test_fail",
            "description": "Failed patch test must block all color services.",
            "canonical_key": None,
            "input": {
                "patch_test_status": "failed",
                "service_intent": "gray_coverage",
                "natural_level": 5,
                "gray_percentage": 40,
            },
            "expected": {
                "recommendation_status": "blocked",
                "matched_rules": ["U001"],
            },
        },
        {
            "case_id": "VC003_retouch_with_refresh",
            "description": "Root retouch with demi refresh on ends.",
            "canonical_key": "Matrix::SoColor::US",
            "input": {
                "service_intent": "gloss_refresh",
                "natural_level": 6,
                "existing_level": 6,
                "gray_percentage": 25,
                "porosity": 5,
                "workflow": "WF_retouch_with_refresh",
            },
            "expected": {
                "recommendation_status": "ok",
                "triggered_workflow": "WF_retouch_with_refresh",
                "formula_zones": ["root", "mid", "end"],
            },
        },
        {
            "case_id": "VC004_virgin_lift_permanent",
            "description": "Virgin hair permanent lift within single-process limits.",
            "canonical_key": "Wella Professionals::Koleston Perfect::US",
            "input": {
                "service_intent": "lift_and_tone",
                "natural_level": 5,
                "desired_level": 7,
                "gray_percentage": 0,
                "porosity": 4,
            },
            "expected": {
                "recommendation_status": "ok",
                "matched_rules": ["W_KP_001", "U008"],
                "developer_volume": 20,
            },
        },
        {
            "case_id": "VC005_prelightened_tonal_control",
            "description": "Tonal Control on pre-lightened hair succeeds.",
            "canonical_key": "Matrix::Tonal Control::US",
            "input": {
                "service_intent": "tone_deposit",
                "pre_lightened": True,
                "existing_level": 9,
                "desired_level": 9,
                "porosity": 6,
            },
            "expected": {
                "recommendation_status": "ok",
                "requires_stage12_inventory_addition": True,
            },
        },
        {
            "case_id": "VC006_gray_blend_matrix_sync",
            "description": "SoColor Sync gray blend at moderate gray percentage.",
            "canonical_key": "Matrix::SoColor Sync::US",
            "input": {
                "service_intent": "gray_coverage",
                "gray_percentage": 45,
                "natural_level": 6,
            },
            "expected": {
                "recommendation_status": "ok",
                "matched_rules": ["M_SYNC_002"],
            },
        },
        {
            "case_id": "VC007_supersync_tint_back",
            "description": "Super Sync tint-back on pre-lightened porous hair.",
            "canonical_key": "Matrix::Super Sync::US",
            "input": {
                "service_intent": "tone_deposit",
                "pre_lightened": True,
                "porosity": 7,
                "existing_level": 8,
            },
            "expected": {
                "recommendation_status": "caution",
                "matched_rules": ["M_SSYNC_001", "U003"],
                "requires_stage12_inventory_addition": True,
            },
        },
        {
            "case_id": "VC008_refresh_restricted_high_porosity",
            "description": "Gloss refresh on high porosity triggers caution and time reduction.",
            "canonical_key": "Redken::Shades EQ Gloss::US",
            "input": {
                "service_intent": "gloss_refresh",
                "porosity": 8,
                "existing_level": 7,
            },
            "expected": {
                "recommendation_status": "caution",
                "matched_rules": ["U010"],
            },
        },
        {
            "case_id": "VC009_coil_gray_ratio",
            "description": "Coil Color requires elevated natural mix for gray.",
            "canonical_key": "Matrix::Coil Color::US",
            "input": {
                "service_intent": "gray_coverage",
                "gray_percentage": 50,
                "texture": "coarse",
            },
            "expected": {
                "recommendation_status": "ok",
                "matched_rules": ["M_COIL_001"],
                "natural_shade_ratio": 0.6,
                "requires_stage12_inventory_addition": True,
            },
        },
        {
            "case_id": "VC010_direct_dye_no_developer",
            "description": "Direct dye line must not assign developer.",
            "canonical_key": "Pulp Riot::Semi-Permanent::US",
            "input": {
                "service_intent": "tone_deposit",
                "line_category": "direct_dye",
            },
            "expected": {
                "recommendation_status": "ok",
                "matched_rules": ["U009"],
                "developer_volume": None,
            },
        },
        {
            "case_id": "VC011_sync_full_gray_cover_prohibited",
            "description": "SoColor Sync blocks full gray cover at high gray percentage.",
            "canonical_key": "Matrix::SoColor Sync::US",
            "input": {
                "service_intent": "gray_coverage",
                "gray_percentage": 85,
            },
            "expected": {
                "recommendation_status": "blocked",
                "matched_rules": ["M_SYNC_001"],
            },
        },
        {
            "case_id": "VC012_supersync_hd_mix_block",
            "description": "Super Sync HD intermixing with standard shades is blocked.",
            "canonical_key": "Matrix::Super Sync::US",
            "input": {
                "selected_sub_ranges": ["HD", "Standard"],
                "service_intent": "tone_deposit",
            },
            "expected": {
                "recommendation_status": "blocked",
                "matched_rules": ["M_SSYNC_002"],
                "requires_stage12_inventory_addition": True,
            },
        },
        {
            "case_id": "VC013_color_does_not_lift_color",
            "description": "Lift on previously colored non-prelightened hair requires correction.",
            "canonical_key": "Redken::Color Gels Lacquers::US",
            "input": {
                "service_intent": "lift_and_tone",
                "existing_artificial_color": "permanent level 5",
                "existing_level": 5,
                "desired_level": 7,
                "pre_lightened": False,
            },
            "expected": {
                "recommendation_status": "requires_consultation",
                "matched_rules": ["U006"],
                "triggered_workflow": "color_correction",
            },
        },
        {
            "case_id": "VC019_wella_colortouch_soft_blend",
            "description": "Color Touch soft blend for low gray percentage.",
            "canonical_key": "Wella Professionals::Color Touch::US",
            "input": {
                "service_intent": "gray_coverage",
                "gray_percentage": 25,
                "natural_level": 6,
            },
            "expected": {
                "recommendation_status": "ok",
                "matched_rules": ["W_CT_001"],
            },
        },
        {
            "case_id": "VC023_pulpriot_direct_dye",
            "description": "Pulp Riot semi-permanent direct application without developer.",
            "canonical_key": "Pulp Riot::Semi-Permanent::US",
            "input": {
                "service_intent": "tone_deposit",
                "line_category": "direct_dye",
                "previous_direct_dye": False,
            },
            "expected": {
                "recommendation_status": "ok",
                "matched_rules": ["U009"],
                "mixing_ratio": "direct_application",
            },
        },
    ],
}

G_CONFLICTS_AND_GAPS: dict = {
    "stage": 13,
    "artifact": "conflicts_and_gaps",
    "generated": GENERATED,
    "conflicts_and_gaps": [
        {
            "gap_id": "G001",
            "gap_type": "inventory_missing",
            "canonical_key": "Matrix::Coil Color::US",
            "severity": "high",
            "details": "Coil Color referenced in Matrix 2023 manual but no normalized shade records in Stage 12 section C.",
            "recommended_next_action": "Add Coil Color to Stage 12 inventory and extract shades before activating line overrides.",
        },
        {
            "gap_id": "G002",
            "gap_type": "inventory_missing",
            "canonical_key": "Matrix::Super Sync::US",
            "severity": "high",
            "details": "Super Sync listed in matrix.com navigation without dedicated product page or shade extraction.",
            "recommended_next_action": "Catalog official Super Sync sources and add normalized shades to Stage 12.",
        },
        {
            "gap_id": "G003",
            "gap_type": "inventory_missing",
            "canonical_key": "Matrix::Tonal Control::US",
            "severity": "medium",
            "details": "Tonal Control Pre-Bonded lacks normalized shade records in Stage 12 section C.",
            "recommended_next_action": "Extract Tonal Control shades and line technical rules in a future batch.",
        },
        {
            "gap_id": "G004",
            "gap_type": "rule_evidence_conflict",
            "severity": "medium",
            "details": "Matrix SoColor resistant gray developer strength: 20 vol in production DDL seed vs 30 vol in manufacturer educator materials.",
            "affected_rules": ["M_SOCOLOR_001", "matrix_socolor_resistant_gray_20vol"],
            "recommended_next_action": "Reconcile against 2023 Matrix haircolor manual and update evidence_status.",
        },
        {
            "gap_id": "G005",
            "gap_type": "workflow_coverage",
            "severity": "low",
            "details": "Pulp Riot FACTION8 permanent line has no Stage 13 line override group; covered only by universal direct-dye rule U009 for semi-permanent.",
            "recommended_next_action": "Add FACTION8 override group when permanent formulation rules are scoped.",
        },
        {
            "gap_id": "G006",
            "gap_type": "schema_alignment",
            "severity": "medium",
            "details": "Stage 13 rule_action keys (set_recommendation_status, block_reason) extend beyond current production engine apply_rule_action surface.",
            "recommended_next_action": "Implement H_schema_extension_proposal actions in rule_evaluator or map at import.",
        },
    ],
}

H_SCHEMA_EXTENSION_PROPOSAL: dict = {
    "stage": 13,
    "artifact": "schema_extension_proposal",
    "generated": GENERATED,
    "completion_status": "proposed",
    "design_basis": "Stage 13 JSON package must load into production formulation_rule, service_workflow, and validation_case tables without losing scope tiers or evidence metadata.",
    "schema_extension_proposal": {
        "new_tables": [
            {
                "table": "service_workflow",
                "columns": [
                    "workflow_id VARCHAR PK",
                    "name VARCHAR",
                    "service_intent VARCHAR",
                    "steps JSONB",
                    "default_zones JSONB",
                    "applicable_line_categories JSONB",
                ],
            },
            {
                "table": "validation_case",
                "columns": [
                    "case_id VARCHAR PK",
                    "description TEXT",
                    "canonical_key VARCHAR NULL",
                    "input JSONB",
                    "expected JSONB",
                    "last_run_at TIMESTAMPTZ NULL",
                    "last_run_status VARCHAR NULL",
                ],
            },
            {
                "table": "formulation_rule_evidence",
                "columns": [
                    "rule_id UUID FK formulation_rule",
                    "source_id UUID FK source_document NULL",
                    "evidence_status VARCHAR",
                    "notes TEXT NULL",
                ],
            },
        ],
        "altered_tables": [
            {
                "table": "formulation_rule",
                "add_columns": [
                    "package_rule_id VARCHAR NULL",
                    "scope_level VARCHAR DEFAULT 'universal'",
                    "canonical_key VARCHAR NULL",
                    "is_dormant BOOL DEFAULT FALSE",
                ],
                "rationale": "Preserve Stage 13 rule_id strings (U001, M_SYNC_001) and dormant state for requires_stage12_inventory_addition groups.",
            }
        ],
        "import_mapping": {
            "universal_rules": "formulation_rule with empty brand/line joins",
            "brand_line_overrides": "formulation_rule + formulation_rule_line via canonical_key → line_region_id",
            "service_workflows": "service_workflow",
            "validation_cases": "validation_case",
        },
    },
}

MANIFEST: dict = {
    "package": "stage13_formulation_rules",
    "stage": 13,
    "generated": GENERATED,
    "completion_status": "complete",
    "counts": {
        "universal_rules": 12,
        "service_workflows": 9,
        "brand_line_overrides": 9,
        "validation_cases": 14,
        "conflicts_and_gaps": 6,
        "dormant_override_groups": 3,
    },
    "sections": {
        "A": "A_formulation_ontology.json",
        "B": "B_universal_rule_library.json",
        "C": "C_service_workflows.json",
        "D": "D_brand_line_overrides.json",
        "E": "E_decision_order.json",
        "F": "F_validation_cases.json",
        "G": "G_conflicts_and_gaps.json",
        "H": "H_schema_extension_proposal.json",
        "I": "I_integration_notes.md",
    },
    "stage12_dependencies": [
        "A_brand_line_inventory.json",
        "C_normalized_shade_records.json",
        "D_line_technical_records.json",
    ],
    "notes": [
        "Override groups with requires_stage12_inventory_addition=true remain dormant until canonical_key appears in Stage 12 section C.",
        "Validation cases VC002, VC014–VC018, VC020–VC022 reserved for future batches.",
        "14 validation cases referenced across package sections F and MANIFEST.",
    ],
}

I_INTEGRATION_NOTES_MD = """# Stage 13 Integration Notes

## Purpose

Stage 13 packages deterministic formulation rules as versioned JSON artifacts (sections A–I) that sit above Stage 12 research data and feed the production formula engine (`hair_color_db/production/`).

## Load order

1. **Stage 12** — `A_brand_line_inventory.json`, `C_normalized_shade_records.json`, `D_line_technical_records.json`
2. **Stage 13 ontology** — `A_formulation_ontology.json` (entities, enums, developer profiles, pigment map)
3. **Universal rules** — `B_universal_rule_library.json` (U001–U012)
4. **Line overrides** — `D_brand_line_overrides.json` via `active_override_groups()` in `loaders.py`
5. **Decision order** — `E_decision_order.json` defines evaluation phases
6. **Production engine** — `run_engine()` in `formula_builder.py`

## Dormant override groups

Three override groups ship with `requires_stage12_inventory_addition: true`:

- `Matrix::Coil Color::US`
- `Matrix::Super Sync::US`
- `Matrix::Tonal Control::US`

`loaders.active_override_groups()` excludes these until the canonical key has normalized shade records in Stage 12 section C.

## Validation cases

`F_validation_cases.json` contains 14 golden-path cases (VC001, VC003–VC013, VC019, VC023). Run against the engine after importing rules to confirm:

- Safety gates (patch test)
- Gray blend vs full cover boundaries
- Direct dye / no-developer paths
- Intermixing blocks (HD, Sync)
- Pre-lightened-only lines (Tonal Control)

## Schema extension

`H_schema_extension_proposal.json` proposes `service_workflow`, `validation_case`, and `formulation_rule_evidence` tables plus dormant-rule columns on `formulation_rule`. Import scripts should map package `rule_id` strings to UUID primary keys while retaining `package_rule_id` for traceability.

## Known gaps

See `G_conflicts_and_gaps.json` (G001–G006) for inventory gaps, evidence conflicts, and engine action-surface alignment items.

## Regenerating artifacts

```bash
python3 hair_color_db/stage13_formulation_rules/emit_artifacts.py
```
"""

ARTIFACT_MAP: dict[str, tuple[str, dict | str]] = {
    "A_formulation_ontology.json": ("json", A_FORMULATION_ONTOLOGY),
    "B_universal_rule_library.json": ("json", B_UNIVERSAL_RULE_LIBRARY),
    "C_service_workflows.json": ("json", C_SERVICE_WORKFLOWS),
    "D_brand_line_overrides.json": ("json", D_BRAND_LINE_OVERRIDES),
    "E_decision_order.json": ("json", E_DECISION_ORDER),
    "F_validation_cases.json": ("json", F_VALIDATION_CASES),
    "G_conflicts_and_gaps.json": ("json", G_CONFLICTS_AND_GAPS),
    "H_schema_extension_proposal.json": ("json", H_SCHEMA_EXTENSION_PROPOSAL),
    "MANIFEST.json": ("json", MANIFEST),
    "I_integration_notes.md": ("md", I_INTEGRATION_NOTES_MD),
}


def write_artifacts() -> list[Path]:
    """Write all Stage 13 package artifacts to the package directory."""
    written: list[Path] = []
    for filename, (kind, content) in ARTIFACT_MAP.items():
        path = PACKAGE_DIR / filename
        if kind == "json":
            with path.open("w", encoding="utf-8") as handle:
                json.dump(content, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
        else:
            path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    paths = write_artifacts()
    for path in paths:
        print(path)
