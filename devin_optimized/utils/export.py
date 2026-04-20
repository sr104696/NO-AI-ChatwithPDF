"""
Export search results to JSON, CSV, and Markdown.

New idea not present in the original sub-projects (the offline_pdf_intelligence
app had CSV export sketched but not fully implemented).  This module gives
users a single ``Exporter`` class that can write results in any of the three
formats.
"""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import List

from ..core.models import SearchResponse


class Exporter:
    """Export a ``SearchResponse`` to various file formats."""

    @staticmethod
    def to_json(response: SearchResponse, indent: int = 2) -> str:
        return json.dumps(response.to_dict(), indent=indent, ensure_ascii=False)

    @staticmethod
    def to_csv(response: SearchResponse) -> str:
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "rank",
            "score",
            "confidence",
            "page",
            "pdf",
            "section",
            "snippet",
            "bm25",
            "tfidf",
            "exact",
        ])
        for i, r in enumerate(response.results, 1):
            writer.writerow([
                i,
                f"{r.score:.4f}",
                r.confidence,
                r.chunk.page_number,
                r.chunk.pdf_name,
                r.chunk.section_heading or "",
                r.snippet,
                f"{r.engine_scores.get('bm25', 0):.4f}",
                f"{r.engine_scores.get('tfidf', 0):.4f}",
                f"{r.engine_scores.get('exact', 0):.4f}",
            ])
        return buf.getvalue()

    @staticmethod
    def to_markdown(response: SearchResponse) -> str:
        lines: List[str] = []
        lines.append(f"# Query: {response.query}")
        lines.append(f"**Type:** {response.query_type}  ")
        lines.append(f"**Chunks searched:** {response.total_chunks_searched}  ")
        lines.append("")

        if response.message:
            lines.append(f"> {response.message}")
            lines.append("")

        for i, r in enumerate(response.results, 1):
            lines.append(f"## Result {i} — {r.confidence} confidence ({r.score:.3f})")
            lines.append(f"**PDF:** {r.chunk.pdf_name}  ")
            lines.append(f"**Page:** {r.chunk.page_number}  ")
            if r.chunk.section_heading:
                lines.append(f"**Section:** {r.chunk.section_heading}  ")
            lines.append("")
            lines.append(r.highlighted_snippet)
            lines.append("")

            if r.entities:
                lines.append("**Entities:**")
                for etype, vals in r.entities.items():
                    lines.append(f"- {etype}: {', '.join(vals)}")
                lines.append("")

            scores_str = ", ".join(
                f"{eng}={sc:.4f}" for eng, sc in r.engine_scores.items()
            )
            lines.append(f"*Engine scores: {scores_str}*")
            lines.append("")
            lines.append("---")
            lines.append("")

        if response.suggestions:
            lines.append("### Suggestions")
            for s in response.suggestions:
                lines.append(f"- {s}")

        return "\n".join(lines)

    @classmethod
    def write(
        cls,
        response: SearchResponse,
        path: str,
        fmt: str = "json",
    ) -> None:
        """
        Write response to a file.

        Args:
            response: The search response.
            path: Output file path.
            fmt: One of ``json``, ``csv``, ``md``.
        """
        converters = {
            "json": cls.to_json,
            "csv": cls.to_csv,
            "md": cls.to_markdown,
            "markdown": cls.to_markdown,
        }
        converter = converters.get(fmt)
        if converter is None:
            raise ValueError(f"Unknown format: {fmt!r}. Use json, csv, or md.")

        content = converter(response)
        Path(path).write_text(content, encoding="utf-8")
