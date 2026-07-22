"""가벼운 PDF 뷰어 + 편집기. 여러 PDF를 탭으로 열어놓고 전환할 수 있다.

실행: python main.py
"""
import os
import sys
import tempfile

import fitz
from PySide6.QtCore import QPoint, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QDockWidget, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QTabWidget, QToolBar,
    QVBoxLayout, QWidget, QSizePolicy,
)

import icons
from canvas import PageCanvas, Tool, TOOL_TR_KEYS, pixmap_from_fitz_pixmap
from capture_overlay import CaptureOverlay
from i18n import available_languages, get_language, set_language, tr
from print_dialog import PrintDialog
from version import APP_DESIGNER, APP_LICENSE, APP_PUBLISHER, APP_STAGE, APP_VERSION

TOOL_ORDER = [
    Tool.NONE, Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKEOUT, Tool.NOTE,
    Tool.FREETEXT, Tool.PEN, Tool.RECT, Tool.ELLIPSE, Tool.ERASER, Tool.EDIT_TEXT,
]

TOOL_ICONS = {
    Tool.NONE: icons.icon_select,
    Tool.HIGHLIGHT: icons.icon_highlight,
    Tool.UNDERLINE: icons.icon_underline,
    Tool.STRIKEOUT: icons.icon_strikeout,
    Tool.NOTE: icons.icon_note,
    Tool.FREETEXT: icons.icon_freetext,
    Tool.PEN: icons.icon_pen,
    Tool.RECT: icons.icon_rect,
    Tool.ELLIPSE: icons.icon_ellipse,
    Tool.ERASER: icons.icon_eraser,
    Tool.EDIT_TEXT: icons.icon_edit_text,
}

# 색상 팔레트 줄은 이 도구들을 고를 때만 나타남(색상을 실제로 쓰는 도구만).
COLOR_TOOLS = {Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKEOUT, Tool.PEN, Tool.RECT, Tool.ELLIPSE}

# 팔레트 줄에 항상 보이는 프리셋 색상(부족하면 "더보기..."로 전체 색상 선택).
PRESET_COLORS = [
    QColor("#e74c3c"), QColor("#e67e22"), QColor("#f1c40f"),
    QColor("#2ecc71"), QColor("#3498db"), QColor("#2c3e50"),
]

THUMB_ZOOM = 0.18


class DocumentView(QWidget):
    """탭 하나 = PDF 문서 하나. 캔버스 + 스크롤 + 찾기바 + 페이지 목록을 갖는다."""

    def __init__(self, main_window: "MainWindow", parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.path: str | None = None
        self.modified = False
        self._last_search_text = None

        self.canvas = PageCanvas()
        self.canvas.documentChanged.connect(lambda v=self: main_window._on_document_changed(v))
        self.canvas.zoomRequested.connect(lambda factor: main_window.set_zoom(self.canvas.zoom * factor))
        self.canvas.pageChanged.connect(main_window._refresh_page_ui)
        self.canvas.undoAvailable.connect(lambda _avail: main_window._sync_undo_redo_actions())
        self.canvas.redoAvailable.connect(lambda _avail: main_window._sync_undo_redo_actions())
        self.canvas.pageContentChanged.connect(lambda idx, v=self: main_window._refresh_one_thumbnail(v, idx))
        self.canvas.sizeChanged.connect(self._resync_page_area)
        self.canvas.captureInserted.connect(
            lambda: main_window.statusBar().showMessage(tr("status_capture_placed")))

        self.page_area = QWidget()
        self.page_area.setStyleSheet("background-color: #6e6e6e;")
        page_area_layout = QVBoxLayout(self.page_area)
        page_area_layout.setContentsMargins(40, 40, 40, 40)
        page_area_layout.addWidget(self.canvas)

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.page_area)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet("QScrollArea { background-color: #6e6e6e; border: none; }")
        self.scroll.verticalScrollBar().valueChanged.connect(lambda v=self: main_window._on_scrolled(v))

        self.search_bar = self._build_search_bar(main_window)

        self.thumb_list = QListWidget()
        self.thumb_list.setIconSize(QSize(100, 140))
        self.thumb_list.setSpacing(6)
        self.thumb_list.currentRowChanged.connect(lambda row, v=self: main_window._on_thumb_selected(v, row))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.search_bar)
        layout.addWidget(self.scroll)

        self.search_bar.hide()

    def _resync_page_area(self):
        self.page_area.layout().activate()
        self.page_area.adjustSize()
        self.page_area.updateGeometry()

    def _build_search_bar(self, main_window: "MainWindow") -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 4, 6, 4)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("search_placeholder"))
        self.search_input.returnPressed.connect(main_window.find_next)
        btn_prev = QPushButton(tr("search_prev"))
        btn_prev.clicked.connect(main_window.find_prev)
        btn_next = QPushButton(tr("search_next"))
        btn_next.clicked.connect(main_window.find_next)
        self.search_count_label = QLabel("")
        self.search_count_label.setFixedWidth(60)
        btn_close = QPushButton("×")
        btn_close.setFixedWidth(28)
        btn_close.clicked.connect(main_window.close_search_bar)
        layout.addWidget(QLabel(tr("search_label")))
        layout.addWidget(self.search_input)
        layout.addWidget(btn_prev)
        layout.addWidget(btn_next)
        layout.addWidget(self.search_count_label)
        layout.addWidget(btn_close)
        return bar

    def label(self) -> str:
        name = os.path.basename(self.path) if self.path else tr("untitled")
        return f"*{name}" if self.modified else name


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("RUMSoft", "PDFEditor")
        set_language(self.settings.value("language", "ko"))

        self.setWindowTitle(tr("app_title"))
        self.resize(1100, 850)

        self._current_tool = Tool.NONE
        self._current_color = QColor(PRESET_COLORS[0])

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.tabs)

        self._build_thumbnail_dock()
        self._build_menu()
        self._build_toolbar()
        self._update_actions_enabled()
        self.setAcceptDrops(True)

        self.page_status_label = QLabel("")
        self.statusBar().addPermanentWidget(self.page_status_label)
        self.statusBar().showMessage(tr("status_ready"))

    # ---------- 탭/문서 뷰 ----------

    def current_view(self) -> DocumentView | None:
        return self.tabs.currentWidget()

    @property
    def canvas(self):
        view = self.current_view()
        return view.canvas if view else None

    @property
    def scroll(self):
        view = self.current_view()
        return view.scroll if view else None

    @property
    def search_bar(self):
        view = self.current_view()
        return view.search_bar if view else None

    @property
    def search_input(self):
        view = self.current_view()
        return view.search_input if view else None

    @property
    def search_count_label(self):
        view = self.current_view()
        return view.search_count_label if view else None

    @property
    def thumb_list(self):
        view = self.current_view()
        return view.thumb_list if view else None

    @property
    def current_path(self):
        view = self.current_view()
        return view.path if view else None

    @current_path.setter
    def current_path(self, value):
        view = self.current_view()
        if view:
            view.path = value

    @property
    def modified(self):
        view = self.current_view()
        return bool(view and view.modified)

    @modified.setter
    def modified(self, value):
        view = self.current_view()
        if view:
            view.modified = value

    @property
    def _last_search_text(self):
        view = self.current_view()
        return view._last_search_text if view else None

    @_last_search_text.setter
    def _last_search_text(self, value):
        view = self.current_view()
        if view:
            view._last_search_text = value

    def _on_tab_changed(self, index: int):
        view = self.tabs.widget(index) if index >= 0 else None
        self.thumb_dock.setWidget(view.thumb_list if view else QListWidget())
        if view:
            view.canvas.set_tool(self._current_tool)
            view.canvas.color = self._current_color
            self._refresh_page_ui()
            self.zoom_label.setText(f"{round(view.canvas.zoom / 1.5 * 100)}%")
            self.act_undo.setEnabled(view.canvas.can_undo())
            self.act_redo.setEnabled(view.canvas.can_redo())
        else:
            self.page_status_label.setText("")
            self.page_spin.setMaximum(1)
            self.page_count_label.setText("/ 0")
            self.act_undo.setEnabled(False)
            self.act_redo.setEnabled(False)
        self._update_actions_enabled()
        self._update_title()

    def _close_tab(self, index: int):
        view = self.tabs.widget(index)
        if view is None:
            return
        if view.modified:
            reply = QMessageBox.question(
                self, tr("exit_title"), tr("exit_msg"), QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        self.tabs.removeTab(index)
        view.deleteLater()

    def _refresh_view_chrome(self, view: DocumentView):
        idx = self.tabs.indexOf(view)
        if idx >= 0:
            self.tabs.setTabText(idx, view.label())
        if view is self.current_view():
            self._update_title()

    def _sync_undo_redo_actions(self):
        has = self.canvas is not None
        self.act_undo.setEnabled(has and self.canvas.can_undo())
        self.act_redo.setEnabled(has and self.canvas.can_redo())

    # ---------- 드래그 앤 드롭 ----------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(
                url.toLocalFile().lower().endswith(".pdf") for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self._open_path(path)

    # ---------- 페이지 썸네일 사이드바 ----------

    def _build_thumbnail_dock(self):
        self.thumb_dock = QDockWidget(tr("thumb_dock_title"), self)
        self.thumb_dock.setWidget(QListWidget())
        self.thumb_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.thumb_dock)

    THUMB_CHUNK_SIZE = 6  # 한 번에 그려서 채우는 썸네일 개수(너무 크면 다시 끊길 수 있음)

    def _rebuild_thumbnails(self):
        """썸네일 목록을 다시 만든다.

        대용량 PDF에서는 페이지 수만큼 즉시 렌더링하면 그동안 화면이 멈추므로,
        일단 아이콘 없는 빈 목록만 즉시 채우고 실제 축소판 그림은
        `_fill_thumbnails_incrementally()`가 조금씩(청크 단위) 나눠서 그린다.
        """
        view = self.current_view()
        if not self.thumb_list or not view:
            return
        self.thumb_list.blockSignals(True)
        self.thumb_list.clear()
        count = view.canvas.doc.page_count if view.canvas.doc else 0
        for i in range(count):
            item = QListWidgetItem(f"{i + 1}")
            item.setTextAlignment(Qt.AlignCenter)
            self.thumb_list.addItem(item)
        self.thumb_list.blockSignals(False)
        self._sync_thumb_selection(self.canvas.page_index)

        view._thumb_gen = getattr(view, "_thumb_gen", 0) + 1
        if count:
            self._fill_thumbnails_incrementally(view, view._thumb_gen, 0)

    def _fill_thumbnails_incrementally(self, view: DocumentView, token: int, start: int):
        # 그 사이 문서를 다시 열었거나(_rebuild_thumbnails가 다시 호출됨) 탭이
        # 닫혔으면 이 예전 작업은 중단한다.
        if getattr(view, "_thumb_gen", None) != token:
            return
        doc = view.canvas.doc
        if not doc:
            return
        try:
            thumb_list = view.thumb_list
        except RuntimeError:
            return  # 탭이 닫혀서 위젯이 이미 삭제됨
        end = min(start + self.THUMB_CHUNK_SIZE, doc.page_count, thumb_list.count())
        mat = fitz.Matrix(THUMB_ZOOM, THUMB_ZOOM)
        for i in range(start, end):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, annots=True)
            pm = pixmap_from_fitz_pixmap(pix)
            thumb_list.item(i).setIcon(QIcon(pm))
        if end < doc.page_count:
            QTimer.singleShot(0, lambda: self._fill_thumbnails_incrementally(view, token, end))

    def _refresh_one_thumbnail(self, view: DocumentView, index: int):
        if not view.canvas.doc or index >= view.thumb_list.count():
            return
        page = view.canvas.doc.load_page(index)
        pix = page.get_pixmap(matrix=fitz.Matrix(THUMB_ZOOM, THUMB_ZOOM), annots=True)
        pm = pixmap_from_fitz_pixmap(pix)
        view.thumb_list.item(index).setIcon(QIcon(pm))

    def _on_thumb_selected(self, view: DocumentView, row: int):
        if row >= 0 and view is self.current_view():
            self.scroll_to_page(row)

    def _sync_thumb_selection(self, index: int):
        if not self.thumb_list:
            return
        self.thumb_list.blockSignals(True)
        self.thumb_list.setCurrentRow(index)
        self.thumb_list.blockSignals(False)

    # ---------- 텍스트 찾기 ----------

    def toggle_search_bar(self):
        if not self.canvas or not self.canvas.doc:
            return
        if self.search_bar.isVisible():
            self.close_search_bar()
        else:
            self.search_bar.show()
            self.search_input.setFocus()
            self.search_input.selectAll()

    def close_search_bar(self):
        if not self.search_bar:
            return
        self.search_bar.hide()
        self.canvas.search_highlight = None
        self.canvas.update()

    def _run_search(self, text: str):
        self.canvas.search_matches = []
        if text and self.canvas.doc:
            for i in range(self.canvas.doc.page_count):
                page = self.canvas.doc.load_page(i)
                for r in page.search_for(text):
                    self.canvas.search_matches.append((i, r))
        self.canvas.search_current = -1

    def _search_and_step(self, step: int):
        if not self.canvas:
            return
        text = self.search_input.text().strip()
        if not text:
            return
        if text != self._last_search_text:
            self._run_search(text)
            self._last_search_text = text
        matches = self.canvas.search_matches
        if not matches:
            self.search_count_label.setText("0 / 0")
            self.canvas.search_highlight = None
            self.canvas.update()
            self.statusBar().showMessage(tr("status_not_found", text=text))
            return
        self.canvas.search_current = (self.canvas.search_current + step) % len(matches)
        self._goto_current_match()

    def find_next(self):
        self._search_and_step(1)

    def find_prev(self):
        self._search_and_step(-1)

    def _goto_current_match(self):
        matches = self.canvas.search_matches
        idx = self.canvas.search_current
        page_idx, rect = matches[idx]
        self.canvas.search_highlight = (page_idx, rect)
        self.search_count_label.setText(f"{idx + 1} / {len(matches)}")
        # rect(page.search_for 결과)는 원본(mediabox) 좌표라서, 회전된 페이지에서는
        # 화면표시 좌표로 옮긴 y값으로 스크롤 위치를 계산해야 실제 위치로 이동한다.
        page = self.canvas.doc.load_page(page_idx)
        disp_y0 = (rect * page.rotation_matrix).y0
        target_y = self.canvas.y() + int(self.canvas.page_tops[page_idx] + disp_y0 * self.canvas.zoom) - 60
        self.scroll.verticalScrollBar().setValue(max(0, target_y))
        self.canvas.update()

    # ---------- UI 구성 ----------

    def _build_menu(self):
        file_menu = self.menuBar().addMenu(tr("menu_file"))
        self.act_open = QAction(tr("open"), self)
        self.act_open.triggered.connect(self.open_file)
        file_menu.addAction(self.act_open)

        self.act_save = QAction(tr("save"), self)
        self.act_save.triggered.connect(self.save_file)
        file_menu.addAction(self.act_save)

        self.act_save_as = QAction(tr("save_as"), self)
        self.act_save_as.triggered.connect(self.save_file_as)
        file_menu.addAction(self.act_save_as)

        file_menu.addSeparator()
        self.act_close_tab = QAction(tr("close_tab"), self)
        self.act_close_tab.setShortcut(QKeySequence.Close)
        self.act_close_tab.triggered.connect(lambda: self._close_tab(self.tabs.currentIndex()))
        file_menu.addAction(self.act_close_tab)

        file_menu.addSeparator()
        self.act_print = QAction(tr("print"), self)
        self.act_print.setShortcut(QKeySequence.Print)
        self.act_print.triggered.connect(self.print_preview)
        file_menu.addAction(self.act_print)

        file_menu.addSeparator()
        act_quit = QAction(tr("exit"), self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        edit_menu = self.menuBar().addMenu(tr("menu_edit"))
        self.act_undo = QAction(tr("undo"), self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_undo.setEnabled(False)
        self.act_undo.triggered.connect(self.undo)
        edit_menu.addAction(self.act_undo)

        self.act_redo = QAction(tr("redo"), self)
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_redo.setEnabled(False)
        self.act_redo.triggered.connect(self.redo)
        edit_menu.addAction(self.act_redo)

        edit_menu.addSeparator()
        self.act_copy = QAction(tr("copy"), self)
        self.act_copy.setShortcut(QKeySequence.Copy)
        self.act_copy.triggered.connect(self.copy_selection)
        edit_menu.addAction(self.act_copy)

        edit_menu.addSeparator()
        self.act_find = QAction(tr("find"), self)
        self.act_find.setShortcut(QKeySequence.Find)
        self.act_find.triggered.connect(self.toggle_search_bar)
        edit_menu.addAction(self.act_find)

        edit_menu.addSeparator()
        self.act_capture = QAction(tr("capture"), self)
        self.act_capture.triggered.connect(self.start_screen_capture)
        edit_menu.addAction(self.act_capture)

        page_menu = self.menuBar().addMenu(tr("menu_page"))
        self.act_insert_page = QAction(tr("insert_page"), self)
        self.act_insert_page.triggered.connect(self.insert_page)
        page_menu.addAction(self.act_insert_page)

        self.act_delete_page = QAction(tr("delete_page"), self)
        self.act_delete_page.triggered.connect(self.delete_page)
        page_menu.addAction(self.act_delete_page)

        self.act_rotate_page = QAction(tr("rotate_page"), self)
        self.act_rotate_page.triggered.connect(self.rotate_page)
        page_menu.addAction(self.act_rotate_page)

        view_menu = self.menuBar().addMenu(tr("menu_view"))
        act_zoom_in = QAction(tr("zoom_in"), self)
        act_zoom_in.triggered.connect(lambda: self.set_zoom(self.canvas.zoom * 1.25))
        view_menu.addAction(act_zoom_in)

        act_zoom_out = QAction(tr("zoom_out"), self)
        act_zoom_out.triggered.connect(lambda: self.set_zoom(self.canvas.zoom / 1.25))
        view_menu.addAction(act_zoom_out)

        act_zoom_reset = QAction(tr("zoom_reset"), self)
        act_zoom_reset.triggered.connect(lambda: self.set_zoom(1.5))
        view_menu.addAction(act_zoom_reset)

        self.act_fit_width = QAction(tr("fit_width"), self)
        self.act_fit_width.triggered.connect(self.fit_width)
        view_menu.addAction(self.act_fit_width)

        self.act_fit_page = QAction(tr("fit_page"), self)
        self.act_fit_page.triggered.connect(self.fit_page)
        view_menu.addAction(self.act_fit_page)

        view_menu.addSeparator()
        self.act_toggle_thumbs = QAction(tr("toggle_thumbnails"), self)
        self.act_toggle_thumbs.triggered.connect(
            lambda: self.thumb_dock.setVisible(not self.thumb_dock.isVisible()))
        view_menu.addAction(self.act_toggle_thumbs)

        lang_menu = self.menuBar().addMenu(tr("menu_language"))
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)
        lang_names = {"ko": "한국어", "en": "English", "zh": "中文", "ja": "日本語"}
        for code in available_languages():
            action = QAction(lang_names.get(code, code), self)
            action.setCheckable(True)
            action.setChecked(code == get_language())
            action.triggered.connect(lambda checked, c=code: self._change_language(c))
            lang_group.addAction(action)
            lang_menu.addAction(action)

        help_menu = self.menuBar().addMenu(tr("menu_help"))
        act_about = QAction(tr("about"), self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

    def _build_toolbar(self):
        # 툴바 하나에 모든 버튼을 다 넣으면, 창 폭이 좁을 때 안 들어가는 버튼들이
        # "»" 오버플로 버튼 뒤로 숨어버려 바로 안 보이는 문제가 있었다. 성격이 다른
        # 그룹별로 줄을 나눠서(각 줄의 폭 요구량을 줄여) 웬만한 창 크기에서는
        # 오버플로 없이 전부 한 번에 보이게 한다.
        file_toolbar = QToolBar("파일/편집")
        file_toolbar.setMovable(False)
        file_toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(file_toolbar)

        self.act_open.setIcon(icons.icon_open())
        self.act_save.setIcon(icons.icon_save())
        self.act_print.setIcon(icons.icon_print())
        self.act_undo.setIcon(icons.icon_undo())
        self.act_redo.setIcon(icons.icon_redo())
        self.act_find.setIcon(icons.icon_find())
        self.act_capture.setIcon(icons.icon_capture())

        file_toolbar.addAction(self.act_open)
        file_toolbar.addAction(self.act_save)
        file_toolbar.addAction(self.act_print)
        file_toolbar.addAction(self.act_undo)
        file_toolbar.addAction(self.act_redo)
        file_toolbar.addAction(self.act_find)
        file_toolbar.addAction(self.act_capture)

        self.addToolBarBreak()
        toolbar = QToolBar("도구")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        # 주석류 도구(선택~텍스트박스)와 그리기류 도구(펜~텍스트수정) 사이에
        # 구분선만 넣고 한 줄에 배치한다(사용자 요청으로 두 줄 → 한 줄로 되돌림).
        half = (len(TOOL_ORDER) + 1) // 2
        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        for i, tool in enumerate(TOOL_ORDER):
            if i == half:
                toolbar.addSeparator()
            action = QAction(TOOL_ICONS[tool](), tr(TOOL_TR_KEYS[tool]), self)
            action.setCheckable(True)
            action.setChecked(tool == Tool.NONE)
            action.triggered.connect(lambda checked, t=tool: self._select_tool(t))
            self.tool_group.addAction(action)
            toolbar.addAction(action)

        # 색상 팔레트 줄 — 색상을 실제로 쓰는 도구(펜/사각형/원/하이라이트/밑줄/
        # 취소선)를 고를 때만 나타남. 늘 떠 있는 "색상" 버튼 하나를 별도로 두는
        # 대신, 필요한 도구를 고를 때만 자연스럽게 등장하게 함.
        self.addToolBarBreak()
        self._build_color_toolbar()

        self.addToolBarBreak()
        nav_toolbar = QToolBar("보기/이동")
        nav_toolbar.setMovable(False)
        self.addToolBar(nav_toolbar)

        act_zoom_out = QAction("-", self)
        act_zoom_out.triggered.connect(lambda: self.set_zoom(self.canvas.zoom / 1.25))
        nav_toolbar.addAction(act_zoom_out)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        nav_toolbar.addWidget(self.zoom_label)

        act_zoom_in = QAction("+", self)
        act_zoom_in.triggered.connect(lambda: self.set_zoom(self.canvas.zoom * 1.25))
        nav_toolbar.addAction(act_zoom_in)

        nav_toolbar.addAction(self.act_fit_width)
        nav_toolbar.addAction(self.act_fit_page)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        nav_toolbar.addWidget(spacer)

        self.act_prev = QAction(tr("prev_page"), self)
        self.act_prev.triggered.connect(self.prev_page)
        nav_toolbar.addAction(self.act_prev)

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.valueChanged.connect(self._on_page_spin_changed)
        nav_toolbar.addWidget(self.page_spin)

        self.page_count_label = QLabel("/ 0")
        nav_toolbar.addWidget(self.page_count_label)

        self.act_next = QAction(tr("next_page"), self)
        self.act_next.triggered.connect(self.next_page)
        nav_toolbar.addAction(self.act_next)

    # ---------- 언어/정보 ----------

    def _change_language(self, code: str):
        self.settings.setValue("language", code)
        QMessageBox.information(self, tr("app_title"), tr("lang_changed"))

    def show_about(self):
        text = (
            f"{tr('app_title')}\n"
            f"{APP_LICENSE}\n\n"
            f"{APP_PUBLISHER}\n"
            f"Rev. {APP_VERSION} ({APP_STAGE})\n"
            f"{tr('about_designed_by', name=APP_DESIGNER)}"
        )
        QMessageBox.about(self, tr("about"), text)

    # ---------- 인쇄 ----------

    def print_preview(self):
        if not self.canvas or not self.canvas.doc:
            return
        dialog = PrintDialog(self.canvas.doc, self.canvas.page_index, self)
        dialog.exec()

    # ---------- 파일 열기/저장 ----------

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("dialog_open_pdf"), "", tr("filter_pdf"))
        if not path:
            return
        self._open_path(path)

    def _open_path(self, path: str):
        norm = os.path.normcase(os.path.normpath(path))
        for i in range(self.tabs.count()):
            v = self.tabs.widget(i)
            if v.path and os.path.normcase(os.path.normpath(v.path)) == norm:
                self.tabs.setCurrentIndex(i)
                return

        try:
            doc = fitz.open(path)
        except Exception as exc:
            QMessageBox.critical(self, tr("open_failed_title"), tr("open_failed_msg", exc=exc))
            return

        view = DocumentView(self)
        view.path = path
        index = self.tabs.addTab(view, view.label())
        self.tabs.setCurrentIndex(index)

        view.canvas.set_tool(self._current_tool)
        view.canvas.color = self._current_color
        view.canvas.load_document(doc)
        view.scroll.verticalScrollBar().setValue(0)
        self._rebuild_thumbnails()
        self._update_actions_enabled()
        self._refresh_view_chrome(view)
        self.statusBar().showMessage(tr("status_opened", path=path))

    def save_file(self):
        if not self.canvas or not self.canvas.doc:
            return
        if not self.current_path:
            self.save_file_as()
            return
        self._save_to(self.current_path)

    def save_file_as(self):
        if not self.canvas or not self.canvas.doc:
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("dialog_save_as"), "", tr("filter_pdf"))
        if not path:
            return
        if self._save_to(path):
            self.current_path = path
            self._refresh_view_chrome(self.current_view())

    def _save_to(self, path: str) -> bool:
        view = self.current_view()
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".pdf", dir=os.path.dirname(path) or ".")
            os.close(fd)
            view.canvas.doc.save(tmp_path)
            os.replace(tmp_path, path)
        except Exception as exc:
            QMessageBox.critical(self, tr("save_failed_title"), tr("save_failed_msg", exc=exc))
            return False
        view.modified = False
        self._refresh_view_chrome(view)
        self.statusBar().showMessage(tr("status_saved", path=path))
        return True

    # ---------- 페이지 이동/확대 (연속 스크롤) ----------

    def prev_page(self):
        if self.canvas:
            self.scroll_to_page(self.canvas.page_index - 1)

    def next_page(self):
        if self.canvas:
            self.scroll_to_page(self.canvas.page_index + 1)

    def _on_page_spin_changed(self, value: int):
        if self.canvas:
            self.scroll_to_page(value - 1)

    def scroll_to_page(self, index: int):
        """해당 페이지의 맨 위가 화면 위쪽에 오도록 스크롤을 이동."""
        if not self.canvas:
            return
        tops = self.canvas.page_tops
        if not tops:
            return
        index = max(0, min(index, len(tops) - 1))
        target_y = self.canvas.y() + int(tops[index])
        self.scroll.verticalScrollBar().setValue(target_y)

    def _current_center_page(self) -> int:
        """지금 화면 가운데에 보이는 페이지 번호를 계산."""
        if not self.canvas:
            return 0
        viewport = self.scroll.viewport()
        canvas_top_in_viewport = self.canvas.mapTo(viewport, QPoint(0, 0)).y()
        center_y = -canvas_top_in_viewport + viewport.height() / 2
        tops = self.canvas.page_tops
        for i, top in enumerate(tops):
            if center_y < top + self.canvas.page_sizes[i][1]:
                return i
        return len(tops) - 1 if tops else 0

    def _on_scrolled(self, view: DocumentView):
        if view is not self.current_view():
            return
        if not view.canvas.doc or not view.canvas.page_tops:
            return
        idx = self._current_center_page()
        if idx != view.canvas.page_index:
            view.canvas.page_index = idx
            self._refresh_page_ui()
            self._sync_thumb_selection(idx)

    def _refresh_page_ui(self):
        if not self.canvas or not self.canvas.doc:
            return
        total = self.canvas.doc.page_count
        current = self.canvas.page_index + 1
        self.page_spin.blockSignals(True)
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(total)
        self.page_spin.setValue(current)
        self.page_spin.blockSignals(False)
        self.page_count_label.setText(f"/ {total}")
        self.page_status_label.setText(tr("page_indicator", current=current, total=total))

    def set_zoom(self, zoom: float):
        if not self.canvas:
            return
        self.canvas.set_zoom(zoom)
        self.zoom_label.setText(f"{round(self.canvas.zoom / 1.5 * 100)}%")
        self.scroll_to_page(self.canvas.page_index)

    def fit_width(self):
        if not self.canvas or not self.canvas.doc:
            return
        page = self.canvas.doc.load_page(self.canvas.page_index)
        avail_w = self.scroll.viewport().width() - 2 * 40 - 24
        self.set_zoom(avail_w / page.rect.width)

    def fit_page(self):
        if not self.canvas or not self.canvas.doc:
            return
        page = self.canvas.doc.load_page(self.canvas.page_index)
        viewport = self.scroll.viewport()
        avail_w = viewport.width() - 2 * 40 - 24
        avail_h = viewport.height() - 2 * 40 - 24
        zoom = min(avail_w / page.rect.width, avail_h / page.rect.height)
        self.set_zoom(zoom)

    # ---------- 페이지 편집 ----------

    def insert_page(self):
        if not self.canvas or not self.canvas.doc:
            return
        self.canvas.push_undo()
        new_index = self.canvas.page_index + 1
        self.canvas.doc.insert_page(new_index)
        self.canvas.render_all_pages()
        self.canvas.page_index = new_index
        self._on_document_changed(self.current_view())
        self._refresh_page_ui()
        self._rebuild_thumbnails()
        self.scroll_to_page(new_index)

    def delete_page(self):
        if not self.canvas or not self.canvas.doc or self.canvas.doc.page_count <= 1:
            QMessageBox.warning(self, tr("delete_impossible_title"), tr("delete_impossible_msg"))
            return
        reply = QMessageBox.question(
            self, tr("delete_page_title"), tr("delete_page_msg", n=self.canvas.page_index + 1),
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.canvas.push_undo()
        idx = self.canvas.page_index
        self.canvas.doc.delete_page(idx)
        self.canvas.render_all_pages()
        self.canvas.page_index = min(idx, self.canvas.doc.page_count - 1)
        self._on_document_changed(self.current_view())
        self._refresh_page_ui()
        self._rebuild_thumbnails()
        self.scroll_to_page(self.canvas.page_index)

    def rotate_page(self):
        if not self.canvas or not self.canvas.doc:
            return
        self.canvas.push_undo()
        page = self.canvas.current_page()
        page.set_rotation((page.rotation + 90) % 360)
        self.canvas.render_all_pages()
        self._on_document_changed(self.current_view())
        self._rebuild_thumbnails()
        self.scroll_to_page(self.canvas.page_index)

    def copy_selection(self):
        if self.canvas and self.canvas.copy_to_clipboard():
            self.statusBar().showMessage(tr("status_copied"))

    # ---------- 캡처 ----------

    def start_screen_capture(self):
        if not self.canvas or not self.canvas.doc:
            return
        # 이 창을 숨기지 않는다 — PDF 편집기 자신의 화면(지금 보고 있는 PDF 내용
        # 포함)도 다른 창과 동등하게 캡처 대상이 되어야 한다. `CaptureOverlay`가
        # 스스로 뜨기 "전"에 화면을 미리 캡처해두므로 오버레이 자신은 결과에 안 섞인다.
        self._capture_overlay = CaptureOverlay()
        self._capture_overlay.captured.connect(self._on_capture_captured)
        self._capture_overlay.cancelled.connect(self._on_capture_cancelled)
        self._capture_overlay.start()

    def _on_capture_captured(self, pixmap):
        self._capture_overlay = None
        if not self.canvas or not self.canvas.doc:
            return
        QGuiApplication.clipboard().setPixmap(pixmap)
        self.canvas.begin_image_placement(pixmap)
        self.statusBar().showMessage(tr("status_capture_place"))

    def _on_capture_cancelled(self):
        self._capture_overlay = None

    def undo(self):
        if not self.canvas:
            return
        self.canvas.undo()
        self._refresh_page_ui()
        self._on_document_changed(self.current_view())
        self._rebuild_thumbnails()
        self.scroll_to_page(self.canvas.page_index)

    def redo(self):
        if not self.canvas:
            return
        self.canvas.redo()
        self._refresh_page_ui()
        self._on_document_changed(self.current_view())
        self._rebuild_thumbnails()
        self.scroll_to_page(self.canvas.page_index)

    # ---------- 도구/색상 ----------

    def _build_color_toolbar(self):
        self.color_toolbar = QToolBar(tr("color"))
        self.color_toolbar.setMovable(False)
        self.color_toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(self.color_toolbar)

        self.color_toolbar.addWidget(QLabel(f" {tr('color')}: "))
        self.color_group = QActionGroup(self)
        self.color_group.setExclusive(True)
        self.color_actions: dict[str, QAction] = {}
        for color in PRESET_COLORS:
            action = QAction(icons.swatch_icon(color), color.name(), self)
            action.setCheckable(True)
            action.setToolTip(color.name())
            action.triggered.connect(lambda checked, c=color: self._pick_preset_color(c))
            self.color_group.addAction(action)
            self.color_toolbar.addAction(action)
            self.color_actions[color.name()] = action

        self.act_more_colors = QAction(icons.icon_palette(), tr("more_colors"), self)
        self.act_more_colors.triggered.connect(self.pick_color)
        self.color_toolbar.addAction(self.act_more_colors)

        self._sync_color_toolbar_checked()
        self._sync_color_toolbar_visibility()

    def _sync_color_toolbar_visibility(self):
        self.color_toolbar.setVisible(self._current_tool in COLOR_TOOLS)

    def _sync_color_toolbar_checked(self):
        name = self._current_color.name()
        for color_name, action in self.color_actions.items():
            action.setChecked(color_name == name)

    def _pick_preset_color(self, color: QColor):
        self._current_color = QColor(color)
        if self.canvas:
            self.canvas.color = self._current_color

    def _select_tool(self, tool: Tool):
        self._current_tool = tool
        if self.canvas:
            self.canvas.set_tool(tool)
        self._sync_color_toolbar_visibility()
        self.statusBar().showMessage(tr("status_tool", tool=tr(TOOL_TR_KEYS[tool])))

    def pick_color(self):
        color = QColorDialog.getColor(self._current_color, self, tr("color_dialog_title"))
        if color.isValid():
            self._current_color = color
            if self.canvas:
                self.canvas.color = color
            self._sync_color_toolbar_checked()

    # ---------- 상태 관리 ----------

    def _on_document_changed(self, view: DocumentView):
        view.modified = True
        self._refresh_view_chrome(view)

    def _update_actions_enabled(self):
        has_doc = bool(self.canvas and self.canvas.doc is not None)
        for action in (self.act_save, self.act_save_as, self.act_print,
                       self.act_insert_page,
                       self.act_delete_page, self.act_rotate_page,
                       self.act_prev, self.act_next,
                       self.act_find, self.act_fit_width, self.act_fit_page,
                       self.act_copy, self.act_capture):
            action.setEnabled(has_doc)
        self.color_toolbar.setEnabled(has_doc)
        for action in self.tool_group.actions():
            action.setEnabled(has_doc)
        self.act_close_tab.setEnabled(self.tabs.count() > 0)

    def _update_title(self):
        view = self.current_view()
        if view:
            self.setWindowTitle(f"{view.label()} - {tr('app_title')}")
        else:
            self.setWindowTitle(tr("app_title"))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.search_bar and self.search_bar.isVisible():
            self.close_search_bar()
            return
        if event.key() == Qt.Key_Escape and self.canvas and self.canvas.tool == Tool.CAPTURE_PLACE:
            self.canvas.cancel_image_placement()
            self.statusBar().showMessage(tr("status_capture_cancelled"))
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        unsaved = [self.tabs.widget(i) for i in range(self.tabs.count()) if self.tabs.widget(i).modified]
        if unsaved:
            reply = QMessageBox.question(
                self, tr("exit_title"), tr("exit_msg"),
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    # Windows에서 PDF 파일을 더블클릭해서 열면, 그 파일 경로가 명령줄 인자로 넘어온다.
    for arg in sys.argv[1:]:
        if arg.lower().endswith(".pdf") and os.path.isfile(arg):
            window._open_path(os.path.abspath(arg))
            break
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
