"""Right-side thumbnail panel for quick PDF page navigation."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class ThumbnailPanel(QWidget):
    """Show scrollable page thumbnails and emit a signal when one is clicked."""

    page_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.thumbnail_zoom = 0.2
        self._buttons: list[QToolButton] = []

        self.setMinimumWidth(170)
        self.setMaximumWidth(230)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        title_label = QLabel("Pages")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(title_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        main_layout.addWidget(self.scroll_area)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch(1)
        self.scroll_area.setWidget(self.content_widget)

    def clear(self) -> None:
        """Remove all thumbnails from the panel."""
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._buttons = []

    def set_document(self, document, render_service, current_page: int = 0) -> None:
        """Render and display thumbnails for every page in a PDF document."""
        self.clear()

        for page_index in range(document.page_count):
            pixmap = render_service.render_page(
                document,
                page_index,
                self.thumbnail_zoom,
            )

            button = QToolButton()
            button.setText(str(page_index + 1))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(pixmap.size())
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setCheckable(True)
            button.setAutoRaise(False)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(
                lambda checked=False, selected_page=page_index: self.page_selected.emit(
                    selected_page
                )
            )

            self.content_layout.insertWidget(page_index, button)
            self._buttons.append(button)

        self.set_current_page(current_page)

    def set_current_page(self, page_index: int) -> None:
        """Highlight the thumbnail for the current page."""
        for index, button in enumerate(self._buttons):
            is_current = index == page_index
            button.setChecked(is_current)

            if is_current:
                button.setStyleSheet(
                    "QToolButton { "
                    "border: 3px solid #2f80ed; "
                    "background: #eaf3ff; "
                    "padding: 4px; "
                    "font-weight: bold; "
                    "}"
                )
            else:
                button.setStyleSheet(
                    "QToolButton { "
                    "border: 1px solid #c7c7c7; "
                    "background: #ffffff; "
                    "padding: 4px; "
                    "}"
                )
