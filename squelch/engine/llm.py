"""
LLM processor for Q&A about transcripts.

Uses Ollama's OpenAI-compatible API by default.
"""

import httpx
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM configuration."""
    endpoint: str = "http://localhost:11434/v1/chat/completions"
    model: str = "llama3.1:8b"
    max_tokens: int = 500
    temperature: float = 0.7


class LLMProcessor:
    """Handles LLM queries about the transcript."""

    SYSTEM_PROMPT = """You are a helpful assistant analyzing a meeting transcript.
Answer questions about the transcript concisely and accurately.
If the transcript doesn't contain enough information to answer, say so.
Keep responses brief and to the point."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client = httpx.AsyncClient(timeout=60.0)
        self._history: list[dict] = []
        self._available: bool = False

    async def check_availability(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            # Ping Ollama's API
            response = await self._client.get("http://localhost:11434/api/tags")
            self._available = response.status_code == 200
            return self._available
        except Exception:
            self._available = False
            return False

    @property
    def is_available(self) -> bool:
        """Return whether LLM is available."""
        return self._available

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

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Here is the recent transcript:\n\n{transcript}\n\n---\n\nQuestion: {question}"}
        ]

        try:
            response = await self._client.post(
                self.config.endpoint,
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "stream": False,
                },
            )
            response.raise_for_status()

            data = response.json()
            answer = data["choices"][0]["message"]["content"]

            # Store in history
            self._history.append({
                "question": question,
                "answer": answer,
            })

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