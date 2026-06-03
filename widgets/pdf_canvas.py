"""Widget that displays a rendered PDF page and handles drawing tools."""

import math

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from models.annotation import Annotation, Point


class PdfCanvas(QWidget):
    """Show a PDF page pixmap with a drawable annotation layer on top."""

    annotations_changed = Signal()
    previous_page_requested = Signal()
    next_page_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._zoom = 1.0
        self._annotations: list[Annotation] = []
        self._current_stroke: Annotation | None = None

        self.current_tool = "pen"
        self.pen_color = "#ff0000"
        self.pen_width = 3
        self.eraser_radius = 10
        self._left_arrow_cursor = self._create_arrow_cursor("left")
        self._right_arrow_cursor = self._create_arrow_cursor("right")

        self.setMouseTracking(True)
        self.setMinimumSize(QSize(600, 800))
        self._update_cursor()

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

    def set_tool(self, tool: str) -> None:
        """Set the active drawing tool: select, pen, or eraser."""
        if tool not in {"select", "pen", "eraser"}:
            return

        self.current_tool = tool
        self._current_stroke = None
        self._update_cursor()
        self.update()

    def set_pen_color(self, color: str) -> None:
        """Change the color used for future pen strokes."""
        self.pen_color = color

    def set_pen_width(self, width: int) -> None:
        """Change the width used for future pen strokes."""
        self.pen_width = max(1, width)

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
        """Start pen drawing or erase strokes based on the active tool."""
        if self._pixmap is None or event.button() != Qt.MouseButton.LeftButton:
            return

        if self.current_tool == "select":
            zone = self._navigation_zone(event.position())
            if zone == "previous":
                self.previous_page_requested.emit()
            elif zone == "next":
                self.next_page_requested.emit()
            return

        point = self._to_page_point(event)

        if self.current_tool == "eraser":
            self._erase_near(point)
            return

        if self.current_tool == "pen":
            self._current_stroke = Annotation(
                color=self.pen_color,
                width=self.pen_width,
                points=[point],
            )
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Continue pen drawing or erasing while the mouse is dragged."""
        if self._pixmap is None:
            return

        if self.current_tool == "select":
            self._update_select_cursor(event.position())
            return

        if not event.buttons() & Qt.MouseButton.LeftButton:
            return

        point = self._to_page_point(event)

        if self.current_tool == "eraser":
            self._erase_near(point)
            return

        if self.current_tool == "pen" and self._current_stroke is not None:
            self._current_stroke.points.append(point)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish the current pen stroke and save it in memory."""
        if self._pixmap is None or event.button() != Qt.MouseButton.LeftButton:
            return

        if self.current_tool != "pen" or self._current_stroke is None:
            return

        self._current_stroke.points.append(self._to_page_point(event))

        if len(self._current_stroke.points) > 1:
            self._annotations.append(self._current_stroke)
            self.annotations_changed.emit()

        self._current_stroke = None
        self.update()

    def _to_page_point(self, event: QMouseEvent) -> Point:
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
            QPointF(x * self._zoom, y * self._zoom) for x, y in annotation.points
        ]

        for start, end in zip(scaled_points, scaled_points[1:]):
            painter.drawLine(start, end)

    def _erase_near(self, point: Point) -> None:
        """Delete the topmost stroke near a page-coordinate point."""
        for index in range(len(self._annotations) - 1, -1, -1):
            annotation = self._annotations[index]
            if self._is_annotation_near_point(annotation, point):
                del self._annotations[index]
                self.annotations_changed.emit()
                self.update()
                return

    def _navigation_zone(self, position: QPointF) -> str | None:
        """Return the page navigation zone under the mouse, if any."""
        if self._pixmap is None:
            return None

        left_boundary = self._pixmap.width() * 0.25
        right_boundary = self._pixmap.width() * 0.75

        if position.x() <= left_boundary:
            return "previous"
        if position.x() >= right_boundary:
            return "next"
        return None

    def _update_select_cursor(self, position: QPointF) -> None:
        """Show a left/right arrow cursor over page navigation zones."""
        zone = self._navigation_zone(position)

        if zone == "previous":
            self.setCursor(self._left_arrow_cursor)
        elif zone == "next":
            self.setCursor(self._right_arrow_cursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _is_annotation_near_point(
        self, annotation: Annotation, point: Point
    ) -> bool:
        """Return True when the eraser is close enough to a stroke."""
        if len(annotation.points) < 2:
            return False

        tolerance = max(
            self.eraser_radius / self._zoom,
            annotation.width + (6 / self._zoom),
        )

        for start, end in zip(annotation.points, annotation.points[1:]):
            if self._distance_to_segment(point, start, end) <= tolerance:
                return True

        return False

    @staticmethod
    def _distance_to_segment(point: Point, start: Point, end: Point) -> float:
        """Measure the shortest distance from a point to a line segment."""
        px, py = point
        sx, sy = start
        ex, ey = end

        dx = ex - sx
        dy = ey - sy
        segment_length_squared = dx * dx + dy * dy

        if segment_length_squared == 0:
            return math.hypot(px - sx, py - sy)

        ratio = ((px - sx) * dx + (py - sy) * dy) / segment_length_squared
        ratio = max(0.0, min(1.0, ratio))

        closest_x = sx + ratio * dx
        closest_y = sy + ratio * dy
        return math.hypot(px - closest_x, py - closest_y)

    def _update_cursor(self) -> None:
        """Change the mouse cursor to match the active tool."""
        if self.current_tool == "pen":
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif self.current_tool == "eraser":
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    @staticmethod
    def _create_arrow_cursor(direction: str) -> QCursor:
        """Create a small custom left or right arrow cursor."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#111111"), 2))
        painter.setBrush(QBrush(QColor("#111111")))

        if direction == "left":
            polygon = QPolygonF(
                [
                    QPointF(5, 12),
                    QPointF(15, 4),
                    QPointF(15, 9),
                    QPointF(21, 9),
                    QPointF(21, 15),
                    QPointF(15, 15),
                    QPointF(15, 20),
                ]
            )
        else:
            polygon = QPolygonF(
                [
                    QPointF(19, 12),
                    QPointF(9, 4),
                    QPointF(9, 9),
                    QPointF(3, 9),
                    QPointF(3, 15),
                    QPointF(9, 15),
                    QPointF(9, 20),
                ]
            )

        painter.drawPolygon(polygon)
        painter.end()
        return QCursor(pixmap, 12, 12)
