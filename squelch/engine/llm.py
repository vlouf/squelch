"""
LLM processor for Q&A about transcripts.

Uses Ollama's OpenAI-compatible API by default.
"""

import httpx

from ..config import config, LLMConfig


class LLMProcessor:
    """Handles LLM queries about the transcript."""

    SYSTEM_PROMPT = """You are a helpful assistant analyzing a meeting transcript.
Answer questions about the transcript concisely and accurately.
If the transcript doesn't contain enough information to answer, say so.
Keep responses brief and to the point."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=60.0)
        self._history: list[dict] = []
        self._available: bool = False
        self._model: str | None = config.llm.model
        self._available_models: list[str] = []

    async def check_availability(self) -> bool:
        """Check if Ollama is running and detect available models."""
        try:
            response = await self._client.get("http://localhost:11434/api/tags")
            if response.status_code != 200:
                self._available = False
                return False

            data = response.json()
            self._available_models = [m["name"] for m in data.get("models", [])]

            # If no model specified, use first available
            if not self._model and self._available_models:
                self._model = self._available_models[0]

            # Check if configured model is available
            if self._model and self._model in self._available_models:
                self._available = True
            elif self._available_models:
                # Configured model not found, fall back to first available
                self._model = self._available_models[0]
                self._available = True
            else:
                self._available = False

            return self._available
        except Exception:
            self._available = False
            return False

    @property
    def is_available(self) -> bool:
        """Return whether LLM is available."""
        return self._available

    @property
    def model(self) -> str | None:
        """Return the currently selected model."""
        return self._model

    @property
    def available_models(self) -> list[str]:
        """Return list of available Ollama models."""
        return self._available_models

    async def list_models(self) -> list[str]:
        """Fetch and return list of available models from Ollama."""
        try:
            response = await self._client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                self._available_models = [m["name"] for m in data.get("models", [])]
            return self._available_models
        except Exception:
            return []

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
            return "Error: Ollama is not running. Start it with 'ollama serve'"

        if not self._model:
            return "Error: No model available. Pull a model with 'ollama pull <model>'"

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Here is the recent transcript:\n\n{transcript}\n\n---\n\nQuestion: {question}",
            },
        ]

        try:
            response = await self._client.post(
                config.llm.endpoint,
                json={
                    "model": self._model,
                    "messages": messages,
                    "max_tokens": config.llm.max_tokens,
                    "temperature": config.llm.temperature,
                    "stream": False,
                },
            )
            response.raise_for_status()

            data = response.json()
            answer = data["choices"][0]["message"]["content"]

            # Store in history
            self._history.append(
                {
                    "question": question,
                    "answer": answer,
                }
            )

            return answer

        except httpx.ConnectError:
            self._available = False
            return "Error: Cannot connect to Ollama. Is it running? (ollama serve)"
        except httpx.HTTPStatusError as e:
            return f"Error: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error: {str(e)}"

    @property
    def history(self) -> list[dict]:
        """Get Q&A history."""
        return self._history

    def clear_history(self) -> None:
        """Clear Q&A history."""
        self._history = []

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
