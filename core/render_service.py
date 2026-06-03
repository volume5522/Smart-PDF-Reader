"""Render PDF pages into Qt pixmaps."""

import fitz
from PySide6.QtGui import QImage, QPixmap


class RenderService:
    """Convert PyMuPDF pages to QPixmap objects for display."""

    @staticmethod
    def render_page(document: fitz.Document, page_index: int, zoom: float) -> QPixmap:
        """Render one PDF page at the requested zoom level."""
        page = document.load_page(page_index)
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)

        image = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format.Format_RGB888,
        ).copy()

        return QPixmap.fromImage(image)
