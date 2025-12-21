"""
Summarizer for generating meeting summaries from transcripts.
"""

import httpx
from dataclasses import dataclass

from ..config import config


SUMMARY_PROMPT = """You are analyzing a meeting transcript. Generate a structured summary with the following sections:

1. **Summary**: A brief 2-3 sentence overview of what was discussed.

2. **Key Themes**: Identify 2-5 main themes or topics discussed. For each theme, provide a heading and 2-4 bullet points.

3. **Action Items**: List any tasks, follow-ups, or action items mentioned. Format as a checkbox list. If no clear action items, write "No specific action items identified."

Format your response EXACTLY like this (use markdown):

## Summary
[Your 2-3 sentence summary here]

## Key Themes

### [Theme 1 Name]
- Point one
- Point two

### [Theme 2 Name]
- Point one
- Point two

## Action Items
- [ ] Action item one
- [ ] Action item two

---

Here is the transcript to analyze:

{transcript}
"""


@dataclass
class SummaryResult:
    """Result from summary generation."""
    success: bool
    content: str  # The markdown content (summary sections or error message)
    error: str | None = None


class Summarizer:
    """Generates meeting summaries using LLM."""

    def __init__(self, model: str | None = None):
        """
        Args:
            model: Ollama model to use. If None, uses config default.
        """
        self._client = httpx.AsyncClient(timeout=120.0)  # Longer timeout for summaries
        self._model = model

    async def generate(self, transcript: str) -> SummaryResult:
        """
        Generate a summary from the transcript.

        Args:
            transcript: Full meeting transcript

        Returns:
            SummaryResult with success status and content
        """
        if not transcript.strip():
            return SummaryResult(
                success=False,
                content="",
                error="No transcript to summarize"
            )

        model = self._model or config.llm.model
        if not model:
            return SummaryResult(
                success=False,
                content="",
                error="No LLM model available"
            )

        try:
            response = await self._client.post(
                config.llm.endpoint,
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": SUMMARY_PROMPT.format(transcript=transcript)}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.3,  # Lower temperature for more consistent summaries
                    "stream": False,
                },
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            return SummaryResult(success=True, content=content)

        except httpx.ConnectError:
            return SummaryResult(
                success=False,
                content="",
                error="Cannot connect to Ollama. Summary generation unavailable."
            )
        except httpx.HTTPStatusError as e:
            return SummaryResult(
                success=False,
                content="",
                error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            return SummaryResult(
                success=False,
                content="",
                error=str(e)
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()