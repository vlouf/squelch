"""
LLM processor factory.

Creates the appropriate LLM processor based on configuration.
"""

from ..config import config
from .llm_ollama import OllamaProcessor
from .llm_litellm import LiteLLMProcessor


# Type alias for any LLM processor
LLMProcessor = OllamaProcessor | LiteLLMProcessor


def create_llm_processor() -> OllamaProcessor | LiteLLMProcessor:
    """
    Create an LLM processor based on the configured provider.

    Returns:
        OllamaProcessor for local Ollama, LiteLLMProcessor for cloud providers.
    """
    provider = config.llm.provider.lower()

    if provider == "ollama":
        return OllamaProcessor()
    else:
        # Any other provider uses LiteLLM
        return LiteLLMProcessor(model=config.llm.model)


__all__ = ["create_llm_processor", "LLMProcessor", "OllamaProcessor", "LiteLLMProcessor"]