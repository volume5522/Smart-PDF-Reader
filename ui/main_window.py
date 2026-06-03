"""Main window and toolbar controls for PDF EBOOK Reader."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolBar,
    QWidget,
)

from core.annotation_store import AnnotationStore
from core.pdf_document import PdfDocument
from core.render_service import RenderService
from widgets.pdf_canvas import PdfCanvas


class MainWindow(QMainWindow):
    """Build the app window and connect user actions to PDF behavior."""

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

        self.page_label = QLabel("No PDF")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidgetResizable(False)
        self.setCentralWidget(self.scroll_area)

        self._build_toolbar()
        self._update_controls()

    def _build_toolbar(self) -> None:
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
            self.zoom = max(0.25, min(self.store.zoom, 5.0))
            self.document.set_page(self.store.last_page)
            self._render_current_page()
        except Exception as error:
            self.document.close()
            self.canvas.clear()
            QMessageBox.critical(self, "PDF 열기 실패", f"PDF를 열 수 없습니다.\n{error}")

        self._update_controls()

    def previous_page(self) -> None:
        """Move to the previous PDF page."""
        if not self.document.is_open:
            return

        self._remember_current_annotations()
        if self.document.previous_page():
            self._render_current_page()
        self._update_controls()

    def next_page(self) -> None:
        """Move to the next PDF page."""
        if not self.document.is_open:
            return

        self._remember_current_annotations()
        if self.document.next_page():
            self._render_current_page()
        self._update_controls()

    def zoom_in(self) -> None:
        """Increase the PDF rendering zoom."""
        if not self.document.is_open:
            return

        self._remember_current_annotations()
        self.zoom = min(self.zoom + 0.25, 5.0)
        self._render_current_page()
        self._update_controls()

    def zoom_out(self) -> None:
        """Decrease the PDF rendering zoom."""
        if not self.document.is_open:
            return

        self._remember_current_annotations()
        self.zoom = max(self.zoom - 0.25, 0.25)
        self._render_current_page()
        self._update_controls()

    def save_notes(self) -> None:
        """Save annotations, zoom, and the last-read page to JSON."""
        if not self.document.is_open:
            return

        self._remember_current_annotations()
        try:
            self.store.save(self.document.current_page, self.zoom)
            QMessageBox.information(self, "저장 완료", "필기 데이터가 저장되었습니다.")
        except OSError as error:
            QMessageBox.critical(self, "저장 실패", f"필기 데이터를 저장할 수 없습니다.\n{error}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Keep the latest in-memory annotations before the window closes."""
        if self.document.is_open:
            self._remember_current_annotations()
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

    def _remember_current_annotations(self) -> None:
        """Copy the canvas annotations into the JSON store state."""
        if not self.document.is_open:
            return

        self.store.set_page_annotations(
            self.document.current_page,
            self.canvas.annotations(),
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
