"""Widget that displays a rendered PDF page and handles pen drawing."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from models.annotation import Annotation


class PdfCanvas(QWidget):
    """Show a PDF page pixmap with a drawable annotation layer on top."""

    annotations_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._zoom = 1.0
        self._annotations: list[Annotation] = []
        self._current_stroke: Annotation | None = None
        self.pen_color = "#ff0000"
        self.pen_width = 3

        self.setMouseTracking(True)
        self.setMinimumSize(QSize(600, 800))

    def set_page(
        self, pixmap: QPixmap, zoom: float, annotations: list[Annotation]
    ) -> None:
        """Display a rendered page and its saved annotations."""
        self._pixmap = pixmap
        self._zoom = zoom
        self._annotations = list(annotations)
        self._current_stroke = None
        self.setFixedSize(pixmap.size())
        self.update()

    def clear(self) -> None:
        """Clear the canvas when no PDF is open."""
        self._pixmap = None
        self._annotations = []
        self._current_stroke = None
        self.setMinimumSize(QSize(600, 800))
        self.update()

    def annotations(self) -> list[Annotation]:
        """Return the annotations currently drawn on this page."""
        return list(self._annotations)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the PDF page image and all pen strokes."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f2f2f2"))

        if self._pixmap is None:
            painter.end()
            return

        painter.drawPixmap(0, 0, self._pixmap)

        for annotation in self._annotations:
            self._draw_annotation(painter, annotation)

        if self._current_stroke is not None:
            self._draw_annotation(painter, self._current_stroke)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start a new pen stroke when the left mouse button is pressed."""
        if self._pixmap is None or event.button() != Qt.MouseButton.LeftButton:
            return

        point = self._to_page_point(event)
        self._current_stroke = Annotation(
            color=self.pen_color,
            width=self.pen_width,
            points=[point],
        )
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Append points while dragging the left mouse button."""
        if self._current_stroke is None:
            return

        if not event.buttons() & Qt.MouseButton.LeftButton:
            return

        self._current_stroke.points.append(self._to_page_point(event))
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish the current pen stroke and save it in memory."""
        if self._current_stroke is None or event.button() != Qt.MouseButton.LeftButton:
            return

        self._current_stroke.points.append(self._to_page_point(event))

        if len(self._current_stroke.points) > 1:
            self._annotations.append(self._current_stroke)
            self.annotations_changed.emit()

        self._current_stroke = None
        self.update()

    def _to_page_point(self, event: QMouseEvent) -> tuple[float, float]:
        """Convert widget coordinates to unscaled PDF page coordinates."""
        position = event.position()
        return (position.x() / self._zoom, position.y() / self._zoom)

    def _draw_annotation(self, painter: QPainter, annotation: Annotation) -> None:
        """Draw a single annotation in widget coordinates."""
        if len(annotation.points) < 2:
            return

        pen = QPen(QColor(annotation.color))
        pen.setWidthF(max(1.0, annotation.width * self._zoom))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        scaled_points = [
            (x * self._zoom, y * self._zoom) for x, y in annotation.points
        ]

        for start, end in zip(scaled_points, scaled_points[1:]):
            painter.drawLine(start[0], start[1], end[0], end[1])
