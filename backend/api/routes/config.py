"""
config.py - REST endpoints for application configuration.

GET  /api/config          — get current app config
PUT  /api/config          — update app config
POST /api/config/reset    — reset to defaults
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])

APP_CONFIG_PATH = Path(__file__).parent.parent.parent / "app_config.json"

DEFAULT_CONFIG = {
    "lims_system": None,          # "LabWare" | "LabVantage" | "Veeva" | null
    "document_types": [           # Available doc types for upload selection
        "Auto-detect",
        "STP",
        "PTP",
        "SPEC",
        "METHOD",
        "SOP",
        "OTHER",
    ],
    "enabled_sheets": [           # Which LIMS sheets to extract
        "analysis_types",
        "common_names",
        "analysis",
        "components",
        "units",
        "products",
        "product_specs",
        "customers",
        "instruments",
        "lims_users",
        "vendors",
        "suppliers",
        "process_schedules",
        "lists",
        "list_entries",
    ],
    "ai": {
        "temperature": 0.1,
        "max_tokens": 4096,
        "chunk_size": 4000,
        "chunk_overlap": 400,
    },
    "confidence_threshold": 0.6,  # Below this → yellow highlight
    "export_format": "xlsx",
    # User-defined load sheet templates — pasted column headers / structure
    # per LIMS system. Injected into agent prompts as {load_sheet_template}.
    "load_sheet_templates": {
        "LabWare": "",
        "LabVantage": "",
        "Veeva": "",
    },
}


def _load_config() -> dict:
    if APP_CONFIG_PATH.exists():
        try:
            saved = json.loads(APP_CONFIG_PATH.read_text())
            return {
                **DEFAULT_CONFIG,
                **saved,
                "ai": {**DEFAULT_CONFIG["ai"], **saved.get("ai", {})},
                "load_sheet_templates": {
                    **DEFAULT_CONFIG["load_sheet_templates"],
                    **saved.get("load_sheet_templates", {}),
                },
            }
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def _save_config(config: dict) -> None:
    APP_CONFIG_PATH.write_text(json.dumps(config, indent=2))


class ConfigUpdate(BaseModel):
    lims_system: str | None = None
    enabled_sheets: list[str] | None = None
    confidence_threshold: float | None = None
    export_format: str | None = None
    ai: dict | None = None
    load_sheet_templates: dict[str, str] | None = None


@router.get("", summary="Get application configuration")
async def get_config():
    return _load_config()


@router.put("", summary="Update application configuration")
async def update_config(body: ConfigUpdate):
    config = _load_config()
    if body.lims_system is not None:
        config["lims_system"] = body.lims_system
    if body.enabled_sheets is not None:
        config["enabled_sheets"] = body.enabled_sheets
    if body.confidence_threshold is not None:
        config["confidence_threshold"] = body.confidence_threshold
    if body.export_format is not None:
        config["export_format"] = body.export_format
    if body.ai is not None:
        config["ai"] = {**config.get("ai", {}), **body.ai}
    if body.load_sheet_templates is not None:
        config["load_sheet_templates"] = {
            **config.get("load_sheet_templates", {}),
            **body.load_sheet_templates,
        }
    _save_config(config)
    return config


@router.post("/reset", summary="Reset configuration to defaults")
async def reset_config():
    _save_config(dict(DEFAULT_CONFIG))
    return DEFAULT_CONFIG
