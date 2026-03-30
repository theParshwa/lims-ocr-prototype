"""
prompts.py - LLM prompt templates for LIMS document extraction.

The main extraction is handled by the combined prompt in entity_extractor.py.
This module contains the document classifier prompt and helper prompts.
"""

from __future__ import annotations


# ── Document classifier prompt ─────────────────────────────────────────────

CLASSIFIER_SYSTEM = """You are an expert LIMS (Laboratory Information Management System) document analyst.
Your task is to classify the type of laboratory document provided."""

CLASSIFIER_USER = """Analyse this document excerpt and determine its type.

Document text (first 3000 characters):
{text}

Respond with a JSON object ONLY (no markdown, no explanation):
{{
  "document_type": "STP" | "PTP" | "SPEC" | "METHOD" | "SOP" | "OTHER",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "detected_sections": ["list", "of", "detected", "section", "headings"],
  "product_hints": ["any product names found"],
  "analysis_hints": ["any analysis/test method names found"]
}}"""
