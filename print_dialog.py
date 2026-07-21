"""자체 인쇄 대화상자.

Windows 기본 인쇄창(QPrintDialog)은 미리보기를 지원하지 않아서, 프린터 선택·
인쇄 방향·매수·페이지 범위를 전부 이 창 안에서 고르고 바로 미리보기까지
보여준다. Windows 인쇄창은 아예 띄우지 않는다.
"""
import fitz
from PySide6.QtGui import QPageLayout, QPainter
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintPreviewWidget
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QRadioButton, QSpinBox, QVBoxLayout, QWidget,
)

from canvas import pixmap_from_fitz_pixmap
from i18n import tr


def render_to_printer(doc: fitz.Document, printer: QPrinter, page_indices=None):
    """doc의 페이지들을 printer의 실제 인쇄 영역에 맞는 DPI로 다시 그려서 인쇄."""
    indices = list(page_indices) if page_indices is not None else list(range(doc.page_count))
    painter = QPainter(printer)
    try:
        for i, page_index in enumerate(indices):
            if i > 0:
                printer.newPage()
            page = doc.load_page(page_index)
            page_rect = printer.pageRect(QPrinter.DevicePixel)
            zoom = min(page_rect.width() / page.rect.width,
                       page_rect.height() / page.rect.height)
            zoom = max(2.0, min(zoom, 8.33))
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), annots=True)
            img = pixmap_from_fitz_pixmap(pix).toImage()
            x = (page_rect.width() - img.width()) / 2
            y = (page_rect.height() - img.height()) / 2
            painter.drawImage(int(x), int(y), img)
    finally:
        painter.end()


class PrintDialog(QDialog):
    def __init__(self, doc: fitz.Document, current_page_index: int, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.current_page_index = current_page_index
        self.setWindowTitle(tr("print_preview_title"))
        self.resize(950, 680)

        self.printer = QPrinter(QPrinter.HighResolution)
        default_name = QPrinterInfo.defaultPrinterName()
        if default_name:
            self.printer.setPrinterName(default_name)

        self.preview = QPrintPreviewWidget(self.printer)
        self.preview.paintRequested.connect(self._paint)

        left_widget = self._build_controls(default_name)

        zoom_bar = QHBoxLayout()
        btn_zoom_out = QPushButton("-")
        btn_zoom_out.clicked.connect(self.preview.zoomOut)
        btn_zoom_in = QPushButton("+")
        btn_zoom_in.clicked.connect(self.preview.zoomIn)
        btn_fit_width = QPushButton(tr("fit_width"))
        btn_fit_width.clicked.connect(self.preview.fitToWidth)
        btn_fit_page = QPushButton(tr("fit_page"))
        btn_fit_page.clicked.connect(self.preview.fitInView)
        zoom_bar.addWidget(btn_zoom_out)
        zoom_bar.addWidget(btn_zoom_in)
        zoom_bar.addWidget(btn_fit_width)
        zoom_bar.addWidget(btn_fit_page)
        zoom_bar.addStretch(1)

        right = QVBoxLayout()
        right.addLayout(zoom_bar)
        right.addWidget(self.preview)

        root = QHBoxLayout(self)
        root.addWidget(left_widget)
        root.addLayout(right)

        self.preview.fitInView()

    def _build_controls(self, default_name: str) -> QWidget:
        self.printer_combo = QComboBox()
        for info in QPrinterInfo.availablePrinters():
            self.printer_combo.addItem(info.printerName())
        if default_name:
            idx = self.printer_combo.findText(default_name)
            if idx >= 0:
                self.printer_combo.setCurrentIndex(idx)
        self.printer_combo.currentTextChanged.connect(self._on_printer_changed)

        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem(tr("orientation_portrait"), QPageLayout.Portrait)
        self.orientation_combo.addItem(tr("orientation_landscape"), QPageLayout.Landscape)
        self.orientation_combo.currentIndexChanged.connect(self._on_orientation_changed)

        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 99)
        self.copies_spin.setValue(1)

        self.range_all = QRadioButton(tr("page_range_all"))
        self.range_current = QRadioButton(tr("page_range_current"))
        self.range_all.setChecked(True)
        self.range_all.toggled.connect(self.preview.updatePreview)
        self.range_current.toggled.connect(self.preview.updatePreview)

        btn_print = QPushButton(tr("print"))
        btn_print.clicked.connect(self._do_print)
        btn_cancel = QPushButton(tr("cancel"))
        btn_cancel.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(tr("printer_label")))
        layout.addWidget(self.printer_combo)
        layout.addWidget(QLabel(tr("orientation_label")))
        layout.addWidget(self.orientation_combo)
        layout.addWidget(QLabel(tr("copies_label")))
        layout.addWidget(self.copies_spin)
        layout.addWidget(QLabel(tr("page_range_label")))
        layout.addWidget(self.range_all)
        layout.addWidget(self.range_current)
        layout.addStretch(1)
        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_print)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setFixedWidth(200)
        return widget

    def _page_indices(self):
        if self.range_current.isChecked():
            return [self.current_page_index]
        return None

    def _paint(self, printer):
        render_to_printer(self.doc, printer, self._page_indices())

    def _on_printer_changed(self, name: str):
        self.printer.setPrinterName(name)
        self.preview.updatePreview()

    def _on_orientation_changed(self, _index: int):
        self.printer.setPageOrientation(self.orientation_combo.currentData())
        self.preview.updatePreview()

    def _do_print(self):
        self.printer.setCopyCount(self.copies_spin.value())
        try:
            render_to_printer(self.doc, self.printer, self._page_indices())
        except Exception as exc:
            QMessageBox.critical(self, tr("print_failed_title"), tr("print_failed_msg", exc=exc))
            return
        self.accept()
