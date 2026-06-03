"""Main window and toolbar controls for PDF EBOOK Reader."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QToolBar,
    QWidget,
)

from core.annotation_store import AnnotationStore
from core.pdf_document import PdfDocument
from core.render_service import RenderService
from widgets.page_memo_panel import PageMemoPanel
from widgets.pdf_canvas import PdfCanvas
from widgets.thumbnail_panel import ThumbnailPanel


class MainWindow(QMainWindow):
    """Build the app window and connect user actions to PDF behavior."""

    MIN_ZOOM = 0.5
    MAX_ZOOM = 4.0
    ZOOM_STEP = 0.1

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF EBOOK Reader")
        self.resize(1100, 850)

        self.document = PdfDocument()
        self.renderer = RenderService()
        self.store = AnnotationStore()
        self.zoom = 1.0

        self.canvas = PdfCanvas()
        self.canvas.annotations_changed.connect(self._remember_current_annotations)
        self.canvas.previous_page_requested.connect(self.previous_page)
        self.canvas.next_page_requested.connect(self.next_page)
        self.canvas.zoom_requested.connect(self.handle_zoom_request)
        self.memo_panel = PageMemoPanel()
        self.memo_panel.memo_changed.connect(self._on_memo_changed)
        self.thumbnail_panel = ThumbnailPanel()
        self.thumbnail_panel.page_selected.connect(self.go_to_page)

        self.page_label = QLabel("No PDF")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidgetResizable(False)

        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.addWidget(self.scroll_area)
        self.content_splitter.addWidget(self.memo_panel)
        self.content_splitter.setStretchFactor(0, 5)
        self.content_splitter.setStretchFactor(1, 1)
        self.content_splitter.setSizes([700, 150])

        central_widget = QWidget()
        central_layout = QHBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.content_splitter, 1)
        central_layout.addWidget(self.thumbnail_panel)
        self.setCentralWidget(central_widget)

        self._build_top_toolbar()
        self._build_drawing_toolbar()
        self._update_controls()

    def _build_top_toolbar(self) -> None:
        """Create the top toolbar with PDF and navigation buttons."""
        toolbar = QToolBar("PDF Controls")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.open_button = QPushButton("PDF 열기")
        self.previous_button = QPushButton("이전 페이지")
        self.next_button = QPushButton("다음 페이지")
        self.zoom_in_button = QPushButton("확대")
        self.zoom_out_button = QPushButton("축소")
        self.save_button = QPushButton("저장")

        self.open_button.clicked.connect(self.open_pdf)
        self.previous_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.save_button.clicked.connect(self.save_notes)

        for button in (
            self.open_button,
            self.previous_button,
            self.next_button,
            self.zoom_in_button,
            self.zoom_out_button,
            self.save_button,
        ):
            layout.addWidget(button)

        layout.addStretch(1)
        self.page_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.page_label)

        toolbar.addWidget(container)

    def _build_drawing_toolbar(self) -> None:
        """Create the left drawing toolbar and connect it to the canvas."""
        toolbar = QToolBar("Drawing Tools")
        toolbar.setMovable(False)
        toolbar.setOrientation(Qt.Orientation.Vertical)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)

        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.setExclusive(True)

        self.select_action = self._create_tool_action("선택", "select")
        self.pen_action = self._create_tool_action("펜", "pen")
        self.eraser_action = self._create_tool_action("지우개", "eraser")

        for action in (self.select_action, self.pen_action, self.eraser_action):
            toolbar.addAction(action)

        toolbar.addSeparator()

        self.color_button = QPushButton("색상")
        self.color_button.setToolTip("펜 색상 변경")
        self.color_button.clicked.connect(self.choose_pen_color)
        toolbar.addWidget(self.color_button)

        self.width_label = QLabel("굵기")
        self.width_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.width_label)

        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 30)
        self.width_spinbox.setValue(self.canvas.pen_width)
        self.width_spinbox.setToolTip("펜 굵기 변경")
        self.width_spinbox.valueChanged.connect(self.canvas.set_pen_width)
        toolbar.addWidget(self.width_spinbox)

        self.pen_action.setChecked(True)
        self.canvas.set_tool("pen")
        self._update_color_button()

    def _create_tool_action(self, label: str, tool: str) -> QAction:
        """Create one checkable tool action for the drawing toolbar."""
        action = QAction(label, self)
        action.setCheckable(True)
        action.setData(tool)
        action.setToolTip(f"{label} 도구")
        action.triggered.connect(
            lambda checked=False, selected_tool=tool: self.set_tool(selected_tool)
        )
        self.tool_action_group.addAction(action)
        return action

    def set_tool(self, tool: str) -> None:
        """Set the active canvas tool using clear string states."""
        self.canvas.set_tool(tool)

    def choose_pen_color(self) -> None:
        """Open QColorDialog and apply the selected pen color."""
        selected_color = QColorDialog.getColor(
            QColor(self.canvas.pen_color),
            self,
            "펜 색상 선택",
        )

        if not selected_color.isValid():
            return

        self.canvas.set_pen_color(selected_color.name())
        self._update_color_button()

    def open_pdf(self) -> None:
        """Ask the user for a PDF file and display it."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "PDF 파일 열기",
            str(Path.home()),
            "PDF Files (*.pdf)",
        )

        if not file_name:
            return

        try:
            self.document.open(file_name)
            self.store.load(file_name)
            self.zoom = self._clamp_zoom(self.store.zoom)
            self.document.set_page(self.store.last_page)
            self.thumbnail_panel.set_document(
                self.document.document,
                self.renderer,
                self.document.current_page,
            )
            self.memo_panel.setEnabled(True)
            self._render_current_page()
        except Exception as error:
            self.document.close()
            self.canvas.clear()
            self.memo_panel.clear()
            self.thumbnail_panel.clear()
            QMessageBox.critical(self, "PDF 열기 실패", f"PDF를 열 수 없습니다.\n{error}")

        self._update_controls()

    def go_to_page(self, page_index: int) -> None:
        """Move to a page selected from the thumbnail panel."""
        if not self.document.is_open:
            return

        if page_index == self.document.current_page:
            self.thumbnail_panel.set_current_page(self.document.current_page)
            return

        self._remember_current_page_state()
        self.document.set_page(page_index)
        self._render_current_page()
        self._update_controls()

    def previous_page(self) -> None:
        """Move to the previous PDF page."""
        if not self.document.is_open:
            return

        self._remember_current_page_state()
        if self.document.previous_page():
            self._render_current_page()
        self._update_controls()

    def next_page(self) -> None:
        """Move to the next PDF page."""
        if not self.document.is_open:
            return

        self._remember_current_page_state()
        if self.document.next_page():
            self._render_current_page()
        self._update_controls()

    def zoom_in(self) -> None:
        """Increase the PDF rendering zoom."""
        self._change_zoom(self.ZOOM_STEP)

    def zoom_out(self) -> None:
        """Decrease the PDF rendering zoom."""
        self._change_zoom(-self.ZOOM_STEP)

    def handle_zoom_request(self, direction: int) -> None:
        """Handle a zoom request emitted by the PDF canvas wheel event."""
        if direction > 0:
            self.zoom_in()
        elif direction < 0:
            self.zoom_out()

    def _change_zoom(self, delta: float) -> None:
        """Change zoom safely and re-render the current page."""
        if not self.document.is_open:
            return

        new_zoom = self._clamp_zoom(self.zoom + delta)
        if new_zoom == self.zoom:
            return

        old_zoom = self.zoom
        try:
            self._remember_current_page_state()
            self.zoom = new_zoom
            # TODO: Keep the mouse position fixed while zooming for a smoother feel.
            self._render_current_page()
            self._update_controls()
        except Exception:
            self.zoom = old_zoom
            self._update_controls()

    def _clamp_zoom(self, zoom: float) -> float:
        """Keep zoom inside the supported range."""
        return max(self.MIN_ZOOM, min(float(zoom), self.MAX_ZOOM))

    def save_notes(self) -> None:
        """Save annotations, zoom, and the last-read page to JSON."""
        if not self.document.is_open:
            return

        self._remember_current_page_state()
        try:
            self.store.save(self.document.current_page, self.zoom)
            QMessageBox.information(self, "저장 완료", "필기와 메모가 저장되었습니다.")
        except OSError as error:
            QMessageBox.critical(self, "저장 실패", f"필기 데이터를 저장할 수 없습니다.\n{error}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Keep the latest in-memory annotations before the window closes."""
        if self.document.is_open:
            self._remember_current_page_state()
        super().closeEvent(event)

    def _render_current_page(self) -> None:
        """Render the current page and send it to the canvas."""
        if not self.document.is_open:
            return

        pixmap = self.renderer.render_page(
            self.document.document,
            self.document.current_page,
            self.zoom,
        )
        annotations = self.store.get_page_annotations(self.document.current_page)
        self.canvas.set_page(pixmap, self.zoom, annotations)
        self.thumbnail_panel.set_current_page(self.document.current_page)
        self._load_current_page_memo()

    def _remember_current_page_state(self) -> None:
        """Copy current page annotations and memo text into the store."""
        if not self.document.is_open:
            return

        self.store.set_page_annotations(
            self.document.current_page,
            self.canvas.annotations(),
        )
        self._remember_current_memo()

    def _remember_current_annotations(self) -> None:
        """Copy the canvas annotations into the JSON store state."""
        if not self.document.is_open:
            return

        self.store.set_page_annotations(
            self.document.current_page,
            self.canvas.annotations(),
        )

    def _remember_current_memo(self) -> None:
        """Copy the memo editor text into the store for the current page."""
        if not self.document.is_open:
            return

        self.store.set_page_memo(
            self.document.current_page,
            self.memo_panel.get_memo_text(),
        )

    def _load_current_page_memo(self) -> None:
        """Load the memo text for the current page into the memo panel."""
        if not self.document.is_open:
            self.memo_panel.clear()
            return

        self.memo_panel.setEnabled(True)
        self.memo_panel.set_page(
            self.document.current_page,
            self.store.get_page_memo(self.document.current_page),
        )

    def _on_memo_changed(self, memo_text: str) -> None:
        """Update the current page memo as the user types."""
        if not self.document.is_open:
            return

        self.store.set_page_memo(self.document.current_page, memo_text)

    def _update_color_button(self) -> None:
        """Show the active pen color on the color button."""
        self.color_button.setStyleSheet(
            "QPushButton { "
            f"background-color: {self.canvas.pen_color}; "
            "border: 1px solid #555; padding: 6px; "
            "}"
        )

    def _update_controls(self) -> None:
        """Refresh labels and disable controls when no PDF is open."""
        is_open = self.document.is_open

        self.previous_button.setEnabled(is_open and self.document.current_page > 0)
        self.next_button.setEnabled(
            is_open and self.document.current_page < self.document.page_count - 1
        )
        self.zoom_in_button.setEnabled(is_open)
        self.zoom_out_button.setEnabled(is_open)
        self.save_button.setEnabled(is_open)

        if not is_open:
            self.page_label.setText("No PDF")
            return

        self.page_label.setText(
            f"{self.document.current_page + 1} / {self.document.page_count}  "
            f"Zoom {self.zoom:.2f}x"
        )
