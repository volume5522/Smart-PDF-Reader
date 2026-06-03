"""Load and save annotation JSON files."""

import json
from pathlib import Path
from typing import Any

from models.annotation import Annotation


class AnnotationStore:
    """Store PDF reading state and page annotations in a sidecar JSON file."""

    def __init__(self) -> None:
        self.pdf_path: Path | None = None
        self.notes_path: Path | None = None
        self.last_page: int = 0
        self.zoom: float = 1.0
        self.annotations: dict[int, list[Annotation]] = {}
        self.memos: dict[int, str] = {}

    def load(self, pdf_path: str | Path) -> None:
        """Load notes for a PDF, creating empty state when no JSON exists."""
        self.pdf_path = Path(pdf_path)
        self.notes_path = Path(f"{self.pdf_path}.notes.json")
        self.last_page = 0
        self.zoom = 1.0
        self.annotations = {}
        self.memos = {}

        if not self.notes_path.exists():
            return

        try:
            with self.notes_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return

        self.last_page = int(data.get("last_page", 0))
        self.zoom = float(data.get("zoom", 1.0))
        self.annotations = self._parse_annotations(data.get("annotations", {}))
        self.memos = self._parse_memos(data.get("memos", {}))

    def get_page_annotations(self, page_index: int) -> list[Annotation]:
        """Return a copy of the annotations for one page."""
        return list(self.annotations.get(page_index, []))

    def set_page_annotations(
        self, page_index: int, annotations: list[Annotation]
    ) -> None:
        """Replace annotations for one page."""
        self.annotations[page_index] = list(annotations)

    def get_page_memo(self, page_index: int) -> str:
        """Return the saved memo text for one page."""
        return self.memos.get(page_index, "")

    def set_page_memo(self, page_index: int, memo_text: str) -> None:
        """Replace memo text for one page."""
        self.memos[page_index] = memo_text

    def save(self, last_page: int, zoom: float) -> None:
        """Write the current note state to the sidecar JSON file."""
        if self.pdf_path is None or self.notes_path is None:
            return

        self.last_page = last_page
        self.zoom = zoom

        data = {
            "pdf_path": str(self.pdf_path),
            "last_page": self.last_page,
            "zoom": self.zoom,
            "annotations": {
                str(page): [annotation.to_dict() for annotation in annotations]
                for page, annotations in sorted(self.annotations.items())
            },
            "memos": {
                str(page): memo_text
                for page, memo_text in sorted(self.memos.items())
            },
        }

        with self.notes_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _parse_annotations(raw_annotations: Any) -> dict[int, list[Annotation]]:
        """Convert raw JSON annotation data to Annotation objects."""
        annotations: dict[int, list[Annotation]] = {}

        if not isinstance(raw_annotations, dict):
            return annotations

        for page_key, raw_page_annotations in raw_annotations.items():
            try:
                page_index = int(page_key)
            except ValueError:
                continue

            if not isinstance(raw_page_annotations, list):
                continue

            annotations[page_index] = [
                Annotation.from_dict(item)
                for item in raw_page_annotations
                if isinstance(item, dict)
            ]

        return annotations

    @staticmethod
    def _parse_memos(raw_memos: Any) -> dict[int, str]:
        """Convert raw JSON memo data to a page-indexed dictionary."""
        memos: dict[int, str] = {}

        if not isinstance(raw_memos, dict):
            return memos

        for page_key, memo_text in raw_memos.items():
            try:
                page_index = int(page_key)
            except ValueError:
                continue

            memos[page_index] = str(memo_text)

        return memos
