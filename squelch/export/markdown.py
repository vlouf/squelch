"""
Markdown export for meeting transcripts and summaries.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ..config import config
from ..engine.session import Session
from ..engine.summarizer import SummaryResult


class MarkdownExporter:
    """Exports meeting transcripts and summaries to Markdown files."""
    
    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or config.output.output_dir
        self._ensure_output_dir()
    
    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_filename(self, session: Session) -> Path:
        """Generate a filename based on session start time."""
        timestamp = session.started_at.strftime("%Y-%m-%d_%H%M")
        filename = f"{timestamp}_meeting.md"
        return self.output_dir / filename
    
    def export(
        self, 
        session: Session, 
        summary_result: SummaryResult | None = None
    ) -> Path:
        """
        Export session to a Markdown file.
        
        Args:
            session: The meeting session with transcript
            summary_result: Optional summary from LLM
            
        Returns:
            Path to the created file
        """
        filepath = self.generate_filename(session)
        content = self._build_markdown(session, summary_result)
        
        filepath.write_text(content, encoding="utf-8")
        return filepath
    
    def _build_markdown(
        self, 
        session: Session, 
        summary_result: SummaryResult | None
    ) -> str:
        """Build the markdown content."""
        lines = []
        
        # Header
        date_str = session.started_at.strftime("%Y-%m-%d %H:%M")
        lines.append(f"# Meeting Notes — {date_str}")
        lines.append("")
        
        # Meeting stats
        duration_min = session.duration / 60
        lines.append(f"> **Duration:** {duration_min:.1f} minutes | **Words:** {session.word_count}")
        lines.append("")
        
        # Summary sections (if available)
        if summary_result and summary_result.success:
            lines.append(summary_result.content)
            lines.append("")
        elif summary_result and summary_result.error:
            lines.append("## Summary")
            lines.append("")
            lines.append(f"*Summary unavailable: {summary_result.error}*")
            lines.append("")
        else:
            lines.append("## Summary")
            lines.append("")
            lines.append("*Summary not generated*")
            lines.append("")
        
        # Full transcript in collapsible section
        lines.append("---")
        lines.append("")
        lines.append("## Full Transcript")
        lines.append("")
        lines.append(f"<details>")
        lines.append(f"<summary>Click to expand ({session.word_count} words)</summary>")
        lines.append("")
        lines.append("```")
        
        # Add transcript segments
        for segment in session.segments:
            minutes = int(segment.start_time // 60)
            seconds = int(segment.start_time % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            quality_marker = " ✓" if segment.quality.value == "refined" else ""
            lines.append(f"{timestamp}{quality_marker} {segment.text}")
        
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def open_file(filepath: Path) -> bool:
        """
        Open the file with the system default application.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.run(["open", filepath], check=True)
            else:
                subprocess.run(["xdg-open", filepath], check=True)
            return True
        except Exception:
            return False