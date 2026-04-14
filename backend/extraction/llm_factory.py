"""
llm_factory.py - Create the LangChain LLM client based on config.

Uses Azure OpenAI via LangChain's AzureChatOpenAI.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Instantiate and cache the configured Azure OpenAI LLM.
    """
    from config import settings  # local import to avoid circular

    from langchain_openai import AzureChatOpenAI

    if not settings.azure_openai_api_key:
        raise RuntimeError(
            "AZURE_OPENAI_API_KEY is not set. "
            "Please set it in your .env file or environment."
        )
    logger.info(
        "Using Azure OpenAI deployment: %s (endpoint: %s)",
        settings.azure_openai_deployment,
        settings.azure_openai_endpoint,
    )
    return AzureChatOpenAI(
        azure_deployment=settings.azure_openai_deployment,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
    )
