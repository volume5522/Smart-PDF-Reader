"""Small wrapper around PyMuPDF PDF documents."""

from pathlib import Path

import fitz


class PdfDocument:
    """Manage an opened PDF file and its current page."""

    def __init__(self) -> None:
        self.path: Path | None = None
        self._document: fitz.Document | None = None
        self.current_page: int = 0

    @property
    def is_open(self) -> bool:
        """Return True when a PDF document is loaded."""
        return self._document is not None

    @property
    def page_count(self) -> int:
        """Return the number of pages in the opened PDF."""
        if self._document is None:
            return 0
        return self._document.page_count

    @property
    def document(self) -> fitz.Document:
        """Return the underlying PyMuPDF document."""
        if self._document is None:
            raise RuntimeError("PDF document is not open.")
        return self._document

    def open(self, pdf_path: str | Path) -> None:
        """Open a PDF file and reset the current page to the first page."""
        self.close()
        self.path = Path(pdf_path)
        self._document = fitz.open(str(self.path))
        self.current_page = 0

    def close(self) -> None:
        """Close the current PDF file if one is open."""
        if self._document is not None:
            self._document.close()
        self._document = None
        self.path = None
        self.current_page = 0

    def set_page(self, page_index: int) -> None:
        """Move to a valid page index."""
        if not self.is_open:
            return
        self.current_page = max(0, min(page_index, self.page_count - 1))

    def next_page(self) -> bool:
        """Move to the next page. Return True if the page changed."""
        if not self.is_open or self.current_page >= self.page_count - 1:
            return False
        self.current_page += 1
        return True

    def previous_page(self) -> bool:
        """Move to the previous page. Return True if the page changed."""
        if not self.is_open or self.current_page <= 0:
            return False
        self.current_page -= 1
        return True
