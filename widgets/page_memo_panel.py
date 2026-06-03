"""Page-specific memo editor shown below the PDF canvas."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget


class PageMemoPanel(QWidget):
    """A small memo editor that displays text for the current PDF page."""

    memo_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_loading_memo = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(6)

        self.title_label = QLabel("현재 페이지 메모")
        self.memo_edit = QPlainTextEdit()
        self.memo_edit.setPlaceholderText("이 페이지에 대한 메모를 입력하세요.")
        self.memo_edit.setMinimumHeight(110)
        self.memo_edit.setMaximumHeight(260)
        self.memo_edit.textChanged.connect(self._emit_memo_changed)

        layout.addWidget(self.title_label)
        layout.addWidget(self.memo_edit)
        self.setEnabled(False)

    def set_page(self, page_index: int, memo_text: str) -> None:
        """Load memo text for a page without emitting a false change signal."""
        self._is_loading_memo = True
        self.title_label.setText(f"Page {page_index + 1} Memo")
        self.memo_edit.setPlainText(memo_text)
        self._is_loading_memo = False

    def clear(self) -> None:
        """Clear and disable the memo editor when no PDF is open."""
        self._is_loading_memo = True
        self.title_label.setText("현재 페이지 메모")
        self.memo_edit.clear()
        self._is_loading_memo = False
        self.setEnabled(False)

    def get_memo_text(self) -> str:
        """Return the current memo editor text."""
        return self.memo_edit.toPlainText()

    def _emit_memo_changed(self) -> None:
        """Emit memo text only for user edits, not while loading another page."""
        if self._is_loading_memo:
            return

        self.memo_changed.emit(self.get_memo_text())
