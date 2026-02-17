"""
llm_factory.py - Create the correct LangChain LLM client based on config.

Supports OpenAI (default) and Anthropic Claude.
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

    Import is deferred to avoid mandatory dependency on both providers.
    """
    from config import settings  # local import to avoid circular

    provider = settings.ai_provider.lower()

    if provider == "openai":
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

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Please set it in your .env file or environment."
            )
        logger.info("Using Anthropic model: %s", settings.anthropic_model)
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=settings.ai_temperature,
            max_tokens=settings.ai_max_tokens,
        )

    else:
        raise ValueError(
            f"Unsupported AI provider: '{provider}'. Choose 'openai' or 'anthropic'."
        )
