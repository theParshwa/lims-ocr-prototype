"""
llm_factory.py - Create the LangChain LLM client based on config.

Returns a LangChain chat model with consistent interface.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Instantiate and cache the configured LLM.
    """
    from config import settings  # local import to avoid circular

    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Please set it in your .env file or environment."
        )
    logger.info("Using OpenAI model: %s", settings.openai_model)
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
    )
