"""
LiteLLM processor for cloud LLM providers.

Supports OpenAI, Anthropic, Google, DeepSeek, Mistral, and many more.
API keys should be set via environment variables:
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY
- DEEPSEEK_API_KEY
- etc.
"""

from ..config import config


class LiteLLMProcessor:
    """Handles LLM queries via LiteLLM (cloud providers)."""

    SYSTEM_PROMPT = """You are a helpful assistant analyzing a meeting transcript.
Answer questions about the transcript concisely and accurately.
If the transcript doesn't contain enough information to answer, say so.
Keep responses brief and to the point."""

    def __init__(self, model: str | None = None):
        """
        Args:
            model: Model string like "gpt-4", "claude-sonnet-4-20250514", "gemini/gemini-pro"
        """
        self._model = model or config.llm.model
        self._history: list[dict] = []
        self._available: bool = False
        self._check_import()

    def _check_import(self) -> None:
        """Check if litellm is installed."""
        try:
            import litellm
            self._litellm = litellm
            self._available = True
        except ImportError:
            self._available = False

    async def check_availability(self) -> bool:
        """Check if LiteLLM is available and model is configured."""
        if not self._available:
            return False

        # LiteLLM is available, check if we have a model
        if self._model:
            return True

        return False

    @property
    def is_available(self) -> bool:
        """Return whether LLM is available."""
        return self._available and bool(self._model)

    @property
    def model(self) -> str | None:
        """Return the currently selected model."""
        return self._model

    @property
    def available_models(self) -> list[str]:
        """Return list of suggested models (not exhaustive)."""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "claude-sonnet-4-20250514",
            "claude-haiku-4-20250514",
            "gemini/gemini-1.5-flash",
            "gemini/gemini-1.5-pro",
            "deepseek/deepseek-chat",
            "mistral/mistral-large-latest",
        ]

    async def list_models(self) -> list[str]:
        """Return list of suggested models."""
        return self.available_models

    def set_model(self, model: str) -> None:
        """Set the model to use for queries."""
        self._model = model

    async def ask(self, question: str, transcript: str) -> str:
        """
        Ask a question about the transcript.

        Args:
            question: User's question
            transcript: Recent transcript text for context

        Returns:
            LLM response text
        """
        if not self._available:
            return "Error: LiteLLM not installed. Install with: pip install litellm"

        if not self._model:
            return "Error: No model configured. Set a model in Options."

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Here is the recent transcript:\n\n{transcript}\n\n---\n\nQuestion: {question}"}
        ]

        try:
            # LiteLLM completion is sync, but we can run it
            import asyncio
            response = await asyncio.to_thread(
                self._litellm.completion,
                model=self._model,
                messages=messages,
                max_tokens=config.llm.max_tokens,
                temperature=config.llm.temperature,
            )

            answer = response.choices[0].message.content

            # Store in history
            self._history.append({
                "question": question,
                "answer": answer,
            })

            return answer

        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages
            if "api_key" in error_msg.lower() or "auth" in error_msg.lower():
                return f"Error: API key not set. Set the appropriate environment variable (e.g., OPENAI_API_KEY)"
            return f"Error: {error_msg}"

    @property
    def history(self) -> list[dict]:
        """Get Q&A history."""
        return self._history

    def clear_history(self) -> None:
        """Clear Q&A history."""
        self._history = []

    async def close(self) -> None:
        """Close resources (no-op for LiteLLM)."""
        pass
