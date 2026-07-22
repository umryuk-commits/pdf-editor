"""PDF 페이지를 그리고, 마우스로 주석/편집 작업을 처리하는 캔버스 위젯.

여러 페이지를 위아래로 이어붙여서 그리기 때문에, 스크롤만으로 다음/이전
페이지를 자연스럽게 넘어갈 수 있다(연속 스크롤 뷰).
"""
from enum import Enum

import fitz
from PySide6.QtCore import Qt, QBuffer, QIODevice, QPoint, QRect, QRectF, Signal
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QCursor, QGuiApplication, QTransform,
)
from PySide6.QtWidgets import QWidget, QInputDialog, QMenu

from i18n import tr


class Tool(str, Enum):
    """값은 화면에 보이는 글자가 아니라 내부 식별자 — 표시용 글자는 i18n의
    TOOL_TR_KEYS로 따로 관리한다(다국어 지원)."""
    NONE = "none"
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STRIKEOUT = "strikeout"
    NOTE = "note"
    FREETEXT = "freetext"
    PEN = "pen"
    RECT = "rect"
    ELLIPSE = "ellipse"
    ERASER = "eraser"
    EDIT_TEXT = "edit_text"
    CAPTURE_PLACE = "capture_place"  # 캡처 직후, 페이지 위에 놓을 위치/크기를 정하는 임시 모드


TOOL_TR_KEYS = {
    Tool.NONE: "tool_none",
    Tool.HIGHLIGHT: "tool_highlight",
    Tool.UNDERLINE: "tool_underline",
    Tool.STRIKEOUT: "tool_strikeout",
    Tool.NOTE: "tool_note",
    Tool.FREETEXT: "tool_freetext",
    Tool.PEN: "tool_pen",
    Tool.RECT: "tool_rect",
    Tool.ELLIPSE: "tool_ellipse",
    Tool.ERASER: "tool_eraser",
    Tool.EDIT_TEXT: "tool_edit_text",
}


DRAG_TOOLS = {
    Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKEOUT,
    Tool.FREETEXT, Tool.PEN, Tool.RECT, Tool.ELLIPSE, Tool.EDIT_TEXT,
    Tool.CAPTURE_PLACE,
}
CLICK_TOOLS = {Tool.NOTE, Tool.ERASER}

PAGE_GAP = 20  # 연속 스크롤 시 페이지 사이 간격(회색 배경이 보이는 부분)
MOVABLE_ANNOT_TYPES = {"FreeText"}  # 선택 도구로 이동/크기조절 가능한 주석 종류
HANDLE_SIZE = 6  # 크기조절 손잡이 반지름(픽셀)
HANDLE_CURSORS = {
    "tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor,
    "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor,
}


def _fit_textbox(page: fitz.Page, rect: fitz.Rect, text: str,
                  start_size: float = 11, min_size: float = 6,
                  fontname: str = "helv", color=None, rotate: int = 0):
    """rect에 text가 들어가도록 폰트 크기를 줄여가며 삽입.

    insert_textbox()는 글자가 다 안 들어가면 반환값이 음수이고,
    이 경우 아무 텍스트도 그려지지 않는다 (조용히 버려짐). 그래서
    약간의 여백을 더하고, 안 들어가면 폰트를 줄여서 재시도한다.

    `rotate`는 페이지의 `page.rotation`을 그대로 넘겨야 한다 — 원본 PDF의
    텍스트는 페이지 회전이 적용된 뒤 화면에서 올바로 읽히도록 mediabox
    좌표계 안에서 미리 그만큼 돌아간 방향으로 그려져 있어서, 새로 넣는
    텍스트도 같은 각도로 안 돌리면 회전된 페이지에서 방향이 어긋나 보인다.
    """
    padded = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1 + 4)
    fontsize = start_size
    while fontsize >= min_size:
        rc = page.insert_textbox(padded, text, fontsize=fontsize,
                                  fontname=fontname, color=color, rotate=rotate)
        if rc >= 0:
            return
        fontsize -= 1
    page.insert_textbox(padded, text, fontsize=min_size, fontname=fontname,
                         color=color, rotate=rotate)


def _color_int_to_rgb(value: int) -> tuple:
    return ((value >> 16 & 255) / 255, (value >> 8 & 255) / 255, (value & 255) / 255)


def _map_fontname(fontname: str, flags: int) -> str:
    """원본 폰트 이름/스타일 플래그를 insert_textbox가 지원하는 기본 14종 폰트로 매핑."""
    name = (fontname or "").lower()
    bold = "bold" in name or bool(flags & 16)
    italic = "italic" in name or "oblique" in name or bool(flags & 2)
    if "courier" in name or "mono" in name or "consolas" in name:
        table = {"": "cour", "b": "cobo", "i": "coit", "bi": "cobi"}
    elif "times" in name or "georgia" in name or "serif" in name:
        table = {"": "tiro", "b": "tibo", "i": "tiit", "bi": "tibi"}
    else:
        table = {"": "helv", "b": "hebo", "i": "heit", "bi": "hebi"}
    key = ("b" if bold else "") + ("i" if italic else "")
    return table.get(key, table[""])


def _snap_edit_target(page: fitz.Page, rect: fitz.Rect) -> dict | None:
    """드래그한 rect 안의 실제 글자 위치를 찾아 정확한 좌표로 보정.

    드래그가 살짝 삐뚤어져도 실제 글자의 정확한 테두리(bbox)와 기준선
    좌표(origin)를 알아내서, 수정 후에도 원래 위치에 딱 맞게 다시
    그릴 수 있게 해준다.
    """
    d = page.get_text("dict", clip=rect)
    spans = []
    for block in d.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span.get("text", "").strip():
                    spans.append(span)
    if not spans:
        return None

    x0 = min(s["bbox"][0] for s in spans)
    y0 = min(s["bbox"][1] for s in spans)
    x1 = max(s["bbox"][2] for s in spans)
    y1 = max(s["bbox"][3] for s in spans)
    spans.sort(key=lambda s: (round(s["origin"][1], 1), s["origin"][0]))
    base = spans[0]
    line_ys = {round(s["origin"][1], 1) for s in spans}

    return {
        "rect": fitz.Rect(x0, y0, x1, y1),
        "origin": base["origin"],
        "size": base["size"],
        "color": base["color"],
        "font": base["font"],
        "flags": base["flags"],
        "single_line": len(line_ys) == 1,
    }


def _remaining_width(page: fitz.Page, origin, rotation: int) -> float:
    """origin에서 텍스트가 흐르는 방향(페이지 회전에 따른 방향)으로 원본
    (mediabox) 페이지 끝까지 남은 공간(pt). 회전 없는 페이지는 원래처럼
    +x 방향(오른쪽 끝까지)만 보면 되지만, 90/270도 회전 페이지는 텍스트가
    mediabox 안에서 y축 방향으로 흐르므로(`insert_text`의 `rotate`와 짝을
    이루는 방향, `_fit_textbox` 설명 참고) 그 방향으로 계산해야 한다."""
    mb = page.mediabox
    ox, oy = origin
    if rotation == 90:
        return oy - mb.y0
    if rotation == 180:
        return ox - mb.x0
    if rotation == 270:
        return mb.y1 - oy
    return mb.x1 - ox


def _insert_text_fit(page: fitz.Page, origin, text: str, start_size: float,
                      fontname: str, color, max_width: float, min_size: float = 6,
                      rotate: int = 0):
    """origin(기준선 좌표)에 text를 그리되, max_width를 넘으면 글꼴을 줄여서 맞춘다.

    `rotate`는 `page.rotation`을 그대로 넘겨야 회전된 페이지에서도 기존 글자와
    같은 방향으로 그려진다(자세한 이유는 `_fit_textbox`의 설명 참고).
    """
    fontsize = start_size
    while fontsize > min_size:
        width = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
        if width <= max_width:
            break
        fontsize -= 0.5
    page.insert_text(origin, text, fontsize=fontsize, fontname=fontname,
                      color=color, rotate=rotate)


def pixmap_from_fitz_pixmap(pix: fitz.Pixmap) -> QPixmap:
    fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
    img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
    return QPixmap.fromImage(img)


def _normalized_rect(p1: fitz.Point, p2: fitz.Point) -> fitz.Rect:
    return fitz.Rect(
        min(p1.x, p2.x), min(p1.y, p2.y),
        max(p1.x, p2.x), max(p1.y, p2.y),
    )


def _word_quads_in_rect(page: fitz.Page, rect: fitz.Rect) -> list | None:
    """rect 안에 실제 텍스트가 있으면 그 글자들의 사각형(Quad) 목록을 반환.

    없으면 None을 반환해서 호출부가 rect 자체로 대체(도형 위 등)할 수 있게 한다.
    """
    words = page.get_text("words", clip=rect)
    if not words:
        return None
    return [fitz.Rect(w[:4]).quad for w in words]


def _pencil_cursor() -> QCursor:
    pix = QPixmap(24, 24)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("black"), 2))
    p.drawLine(4, 20, 16, 8)
    p.setBrush(QColor("red"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(14, 6, 5, 5)
    p.end()
    return QCursor(pix, 4, 20)


def _eraser_cursor() -> QCursor:
    pix = QPixmap(24, 24)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("black"), 2))
    p.setBrush(QColor("white"))
    p.drawRect(4, 10, 14, 10)
    p.end()
    return QCursor(pix, 4, 10)


_TOOL_CURSORS: dict[Tool, QCursor] = {}


def cursor_for_tool(tool: "Tool") -> QCursor:
    if not _TOOL_CURSORS:
        _TOOL_CURSORS[Tool.NONE] = QCursor(Qt.ArrowCursor)
        _TOOL_CURSORS[Tool.NOTE] = QCursor(Qt.PointingHandCursor)
        _TOOL_CURSORS[Tool.PEN] = _pencil_cursor()
        _TOOL_CURSORS[Tool.ERASER] = _eraser_cursor()
        for t in (Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKEOUT, Tool.RECT,
                  Tool.ELLIPSE, Tool.FREETEXT, Tool.EDIT_TEXT, Tool.CAPTURE_PLACE):
            _TOOL_CURSORS[t] = QCursor(Qt.CrossCursor)
    return _TOOL_CURSORS.get(tool, QCursor(Qt.ArrowCursor))


class PageCanvas(QWidget):
    """문서의 모든 페이지를 위아래로 이어붙여 렌더링하고, 도구 동작을 처리하는 위젯."""

    documentChanged = Signal()
    statusMessage = Signal(str)
    zoomRequested = Signal(float)
    pageChanged = Signal()
    undoAvailable = Signal(bool)
    redoAvailable = Signal(bool)
    sizeChanged = Signal()
    pageContentChanged = Signal(int)
    captureInserted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: fitz.Document | None = None
        self.page_index = 0
        self.zoom = 1.5
        self.tool = Tool.NONE
        self.color = QColor("red")

        self.page_pixmaps: list[QPixmap | None] = []  # 화면에 보였던 페이지만 채워짐(지연 렌더링 캐시)
        self.page_sizes: list[tuple[int, int]] = []  # 각 페이지의 (너비, 높이) - 렌더링 없이 계산됨
        self.page_tops: list[float] = []
        self._render_order: list[int] = []  # 캐시 페이지 순서(LRU) - 오래된 것부터 비움
        self._render_cache_limit = 24

        self._press_point: QPoint | None = None
        self._current_point: QPoint | None = None
        self._pen_points: list[QPoint] = []
        self._dragging = False
        self._active_page_index: int | None = None

        self._undo_stack: list[tuple[bytes, int]] = []
        self._redo_stack: list[tuple[bytes, int]] = []
        self._undo_limit = 15

        self.search_matches: list[tuple[int, fitz.Rect]] = []
        self.search_current = -1
        self.search_highlight: tuple[int, fitz.Rect] | None = None

        self._pending_capture_pixmap: QPixmap | None = None
        self._tool_before_capture: "Tool" = Tool.NONE

        self.selected_page_idx: int | None = None
        self.selected_xref: int | None = None
        self._selected_page_ref = None
        self._select_drag_mode: str | None = None  # None | "move" | "resize" | "text_select"
        self._select_drag_handle: str | None = None
        self._select_drag_start: QPoint | None = None
        self._select_drag_orig_rect: fitz.Rect | None = None
        self._text_select_page_idx: int | None = None
        self.text_selection: tuple[int, fitz.Rect] | None = None  # (page_idx, pdf 좌표 rect)

        self.setMouseTracking(True)
        self.setCursor(cursor_for_tool(Tool.NONE))

    def set_tool(self, tool: "Tool"):
        self.tool = tool
        self.setCursor(cursor_for_tool(tool))
        if tool != Tool.NONE:
            self.clear_selection()
            self.clear_text_selection()

    # ---------- 캡처 삽입 ----------

    def begin_image_placement(self, pixmap: QPixmap):
        """캡처 결과를 들고, 페이지 위 클릭/드래그로 놓을 위치를 정하는 모드로 전환."""
        self._pending_capture_pixmap = pixmap
        self._tool_before_capture = self.tool
        self.set_tool(Tool.CAPTURE_PLACE)

    def cancel_image_placement(self):
        if self.tool != Tool.CAPTURE_PLACE:
            return
        self._pending_capture_pixmap = None
        self.set_tool(self._tool_before_capture)

    # ---------- 선택(이동/크기조절) ----------

    def clear_selection(self):
        self.selected_page_idx = None
        self.selected_xref = None
        self._select_drag_mode = None
        self.update()

    # ---------- 텍스트 드래그 선택/복사 ----------

    def clear_text_selection(self):
        self.text_selection = None
        self.update()

    def get_selected_text(self) -> str:
        if not self.text_selection or not self.doc:
            return ""
        page_idx, rect = self.text_selection
        page = self.doc.load_page(page_idx)
        return page.get_textbox(rect).strip()

    def copy_to_clipboard(self) -> bool:
        text = self.get_selected_text()
        if not text:
            return False
        QGuiApplication.clipboard().setText(text)
        return True

    def _commit_text_selection(self):
        if self._text_select_page_idx is None or not self._select_drag_start or not self._current_point:
            self.clear_text_selection()
            return
        # 드래그 없이 그냥 클릭만 한 경우(제자리 클릭)는 선택하지 않음 —
        # get_textbox()는 면적이 0인 사각형도 그 자리의 글자와 겹치면 텍스트를
        # 돌려줘서, 안 그러면 클릭만 해도 그 아래 글자 전체가 선택돼 버림.
        if (self._current_point - self._select_drag_start).manhattanLength() < 4:
            self.clear_text_selection()
            return
        page_idx = self._text_select_page_idx
        page = self.doc.load_page(page_idx)
        pdf_p1 = self._to_pdf_point(self._select_drag_start, page_idx, page)
        pdf_p2 = self._to_pdf_point(self._current_point, page_idx, page)
        rect = _normalized_rect(pdf_p1, pdf_p2)
        if page.get_textbox(rect).strip():
            self.text_selection = (page_idx, rect)
        else:
            self.text_selection = None
        self.update()

    def get_selected_annot(self):
        if self.selected_xref is None or not self.doc:
            return None
        page = self.doc.load_page(self.selected_page_idx)
        # PyMuPDF에서 Annot은 자신을 만든 Page 객체가 살아있어야 유효하다.
        # 여기서 page를 지역변수로만 두면 함수가 끝나며 GC돼서 반환한 annot이
        # "annotation not bound to any page" 에러(혹은 세그폴트)를 낼 수 있어서,
        # self에 참조를 붙잡아둔다.
        self._selected_page_ref = page
        for annot in page.annots() or []:
            if annot.xref == self.selected_xref:
                return annot
        return None

    def _find_movable_annot(self, page: fitz.Page, pdf_point: fitz.Point):
        found = None
        for annot in page.annots() or []:
            if annot.type[1] in MOVABLE_ANNOT_TYPES and annot.rect.contains(pdf_point):
                found = annot  # 마지막(가장 위에 그려진) 것을 우선
        return found

    def _annot_widget_rect(self, annot, page_idx: int, page: fitz.Page | None = None) -> QRect:
        """주석의 원본(mediabox) rect를 화면표시(회전 반영) 좌표로 바꿔 위젯 사각형으로 변환.

        `annot.rect`는 항상 원본 좌표계라서, 페이지가 90/270도 회전돼 있으면
        `page.rotation_matrix`로 먼저 화면표시 좌표계로 옮긴 다음에 zoom을 곱해야
        선택 테두리/손잡이가 실제 보이는 위치에 그려진다. 호출부가 이미 페이지를
        불러와 놨으면(`page` 인자) 매번 다시 `load_page()`하지 않고 재사용한다 —
        이 함수는 마우스가 움직일 때마다(호버) 반복 호출될 수 있어서 중요하다.
        """
        top = self.page_tops[page_idx]
        if page is None:
            page = self.doc.load_page(page_idx)
        r = annot.rect * page.rotation_matrix
        z = self.zoom
        return QRect(int(r.x0 * z), int(top + r.y0 * z),
                     int((r.x1 - r.x0) * z), int((r.y1 - r.y0) * z))

    @staticmethod
    def _handle_positions(rect: QRect) -> dict:
        return {
            "tl": rect.topLeft(), "tr": rect.topRight(),
            "bl": rect.bottomLeft(), "br": rect.bottomRight(),
        }

    def _handle_at(self, pos: QPoint, annot=None, page: fitz.Page | None = None) -> str | None:
        """주어진 화면 좌표가 선택된 주석의 크기조절 손잡이 위인지 확인.

        annot을 넘기지 않으면 새로 조회하는데, 한 번의 처리 안에서 이미 다른
        곳에서 조회한 annot이 있다면 그걸 넘겨써야 한다 — get_selected_annot()을
        여러 번 부르면 이전 호출이 붙잡아둔 page 참조가 덮어써져서 이전 annot이
        무효화된다(PyMuPDF는 annot을 만든 Page가 살아있어야 유효).
        """
        if annot is None:
            annot = self.get_selected_annot()
            page = self._selected_page_ref
        if annot is None:
            return None
        rect = self._annot_widget_rect(annot, self.selected_page_idx, page)
        for name, pt in self._handle_positions(rect).items():
            if abs(pos.x() - pt.x()) <= HANDLE_SIZE and abs(pos.y() - pt.y()) <= HANDLE_SIZE:
                return name
        return None

    def _drag_preview_rect(self) -> fitz.Rect:
        """이동/크기조절 중 실시간으로 계산되는 화면표시(display) 좌표 사각형.

        핸들(tl/tr/bl/br)은 화면에 보이는 대로의 위/아래/좌/우이므로, 이 함수는
        항상 화면표시 좌표계에서 계산한다(회전된 페이지에서도 핸들 의미가 항상
        맞도록). `_select_drag_orig_rect`도 화면표시 좌표계로 저장돼 있어야 하고,
        실제로 문서에 반영할 때(`_commit_select_drag`)만 mediabox 좌표계로
        변환한다."""
        dx = (self._current_point.x() - self._select_drag_start.x()) / self.zoom
        dy = (self._current_point.y() - self._select_drag_start.y()) / self.zoom
        r = self._select_drag_orig_rect
        if self._select_drag_mode == "move":
            return fitz.Rect(r.x0 + dx, r.y0 + dy, r.x1 + dx, r.y1 + dy)
        x0, y0, x1, y1 = r.x0, r.y0, r.x1, r.y1
        handle = self._select_drag_handle
        if "l" in handle:
            x0 += dx
        if "r" in handle:
            x1 += dx
        if "t" in handle:
            y0 += dy
        if "b" in handle:
            y1 += dy
        min_size = 20 / self.zoom
        if x1 - x0 < min_size:
            x0 = x1 - min_size if "l" in handle else x0
            x1 = x0 + min_size if "r" in handle else x1
        if y1 - y0 < min_size:
            y0 = y1 - min_size if "t" in handle else y0
            y1 = y0 + min_size if "b" in handle else y1
        return fitz.Rect(x0, y0, x1, y1)

    def _handle_select_press(self, pos: QPoint):
        annot = self.get_selected_annot()
        if annot is not None:
            # _drag_preview_rect()가 화면표시 좌표계로 계산하므로, 드래그 시작
            # 시점의 기준 rect도 같은 좌표계(회전 반영)로 맞춰서 저장한다.
            # get_selected_annot()이 이미 불러온 page를 그대로 재사용한다.
            page = self._selected_page_ref
            display_rect = annot.rect * page.rotation_matrix
            handle = self._handle_at(pos, annot, page)
            if handle:
                self._select_drag_mode = "resize"
                self._select_drag_handle = handle
                self._select_drag_start = pos
                self._select_drag_orig_rect = display_rect
                self._current_point = pos
                return
            if self._annot_widget_rect(annot, self.selected_page_idx, page).contains(pos):
                self._select_drag_mode = "move"
                self._select_drag_start = pos
                self._select_drag_orig_rect = display_rect
                self._current_point = pos
                return

        page_idx = self.page_at_y(pos.y())
        if page_idx is None:
            self.clear_selection()
            self.clear_text_selection()
            return
        page = self.doc.load_page(page_idx)
        pdf_point = self._to_pdf_point(pos, page_idx, page)
        found = self._find_movable_annot(page, pdf_point)
        if found is not None:
            self.selected_page_idx = page_idx
            self.selected_xref = found.xref
            self.clear_text_selection()
        else:
            self.clear_selection()
            self.clear_text_selection()
            # 주석이 아니면 텍스트 드래그 선택 시작(놓을 때 _commit_text_selection에서 확정)
            self._select_drag_mode = "text_select"
            self._select_drag_start = pos
            self._current_point = pos
            self._text_select_page_idx = page_idx
        self.update()

    def _update_hover_cursor(self, pos: QPoint):
        # 이 함수는 마우스가 캔버스 위에서 움직일 때마다 호출되므로, 여기서
        # `doc.load_page()`를 반복 호출하면 그만큼 매 프레임 비용이 든다 —
        # get_selected_annot()이 이미 불러온 page(`_selected_page_ref`)를
        # 계속 재사용해서 중복 로드를 피한다.
        annot = self.get_selected_annot()
        selected_page = self._selected_page_ref if annot is not None else None
        handle = self._handle_at(pos, annot, selected_page)
        if handle:
            self.setCursor(QCursor(HANDLE_CURSORS[handle]))
            return
        if annot is not None and self._annot_widget_rect(annot, self.selected_page_idx, selected_page).contains(pos):
            self.setCursor(QCursor(Qt.SizeAllCursor))
            return
        page_idx = self.page_at_y(pos.y())
        if page_idx is not None and self.doc:
            page = self.doc.load_page(page_idx)
            pdf_point = self._to_pdf_point(pos, page_idx, page)
            if self._find_movable_annot(page, pdf_point) is None:
                self.setCursor(QCursor(Qt.IBeamCursor))
                return
        self.setCursor(cursor_for_tool(Tool.NONE))

    def _commit_select_drag(self):
        annot = self.get_selected_annot()
        if annot is None:
            return
        page = self.doc.load_page(self.selected_page_idx)
        # _drag_preview_rect()는 화면표시 좌표계라서, 저장 직전에 원본(mediabox)
        # 좌표계로 되돌려야 한다.
        new_rect = self._drag_preview_rect() * page.derotation_matrix
        self.push_undo()
        annot.set_rect(new_rect)
        annot.update()
        self.render_single_page(self.selected_page_idx)
        self.documentChanged.emit()
        self.pageContentChanged.emit(self.selected_page_idx)

    # ---------- 문서/페이지 관리 ----------

    def load_document(self, doc: fitz.Document):
        self.doc = doc
        self.page_index = 0
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.search_matches = []
        self.search_current = -1
        self.search_highlight = None
        self.selected_page_idx = None
        self.selected_xref = None
        self._select_drag_mode = None
        self.text_selection = None
        self.undoAvailable.emit(False)
        self.redoAvailable.emit(False)
        self.render_all_pages()
        self.pageChanged.emit()

    def page_count(self) -> int:
        return self.doc.page_count if self.doc else 0

    def current_page(self) -> fitz.Page:
        return self.doc.load_page(self.page_index)

    def page_at_y(self, y: float) -> int | None:
        """캔버스 좌표 y가 속한 페이지 번호를 찾는다(페이지 사이 간격이면 None)."""
        for i, top in enumerate(self.page_tops):
            if top <= y <= top + self.page_sizes[i][1]:
                return i
        return None

    def set_zoom(self, zoom: float):
        self.zoom = max(0.25, min(zoom, 5.0))
        self.render_all_pages()

    def render_all_pages(self):
        """문서의 페이지 배치(크기·위치)를 다시 계산한다.

        확대/축소, 페이지 삽입·삭제·회전, 문서 열기처럼 페이지 배치 자체가
        바뀔 때 호출한다. **실제 픽셀 렌더링은 여기서 하지 않음** — 각 페이지의
        크기는 `page.rect`만으로 계산할 수 있어 매우 가볍고, 실제 렌더링은
        화면에 보이는 순간 paintEvent에서 지연 처리된다(대용량 PDF에서 문서를
        열 때/확대할 때마다 수백 페이지를 전부 미리 그려서 멈추는 문제를 막기 위함).
        """
        sizes: list[tuple[int, int]] = []
        tops: list[float] = []
        max_w = 1
        y = 0.0
        if self.doc:
            for i in range(self.doc.page_count):
                page = self.doc.load_page(i)
                w = max(1, round(page.rect.width * self.zoom))
                h = max(1, round(page.rect.height * self.zoom))
                sizes.append((w, h))
                tops.append(y)
                max_w = max(max_w, w)
                y += h + PAGE_GAP

        self.page_sizes = sizes
        self.page_tops = tops
        self.page_pixmaps = [None] * len(sizes)
        self._render_order = []
        total_height = max(1, int(y - PAGE_GAP)) if sizes else 1
        self.setFixedSize(max_w, total_height)
        self.update()
        self.sizeChanged.emit()

    def _ensure_page_rendered(self, index: int) -> QPixmap | None:
        """index번 페이지가 아직 캐시에 없으면 그 자리에서 렌더링해서 캐싱.

        paintEvent가 화면에 실제로 보이는 페이지에 대해서만 이 함수를 부르므로,
        문서를 열거나 확대할 때 페이지 전체를 미리 그리지 않아도 됨. 캐시가
        너무 커지지 않도록 오래된(LRU) 페이지는 자동으로 비움.
        """
        if not self.doc or index >= len(self.page_pixmaps):
            return None
        pm = self.page_pixmaps[index]
        if pm is None:
            page = self.doc.load_page(index)
            mat = fitz.Matrix(self.zoom, self.zoom)
            pix = page.get_pixmap(matrix=mat, annots=True)
            pm = pixmap_from_fitz_pixmap(pix)
            self.page_pixmaps[index] = pm
        if index in self._render_order:
            self._render_order.remove(index)
        self._render_order.append(index)
        while len(self._render_order) > self._render_cache_limit:
            evict = self._render_order.pop(0)
            if evict < len(self.page_pixmaps):
                self.page_pixmaps[evict] = None
        return pm

    def render_single_page(self, index: int | None):
        """페이지 크기가 안 바뀌는 편집(주석 추가 등) 후 그 페이지만 다시 그림."""
        if not self.doc or index is None or index >= len(self.page_pixmaps):
            return
        self.page_pixmaps[index] = None  # 캐시 무효화 후 다시 그리게 함
        self._ensure_page_rendered(index)
        self.update()

    # ---------- 좌표 변환 ----------

    def _to_pdf_point(self, widget_point: QPoint, page_index: int,
                      page: fitz.Page | None = None) -> fitz.Point:
        """화면(위젯) 좌표를 주석/편집 API가 기대하는 원본(mediabox) 좌표로 변환.

        `page.rect`(=화면에 렌더링되는 크기)는 페이지가 90/270도 회전되어 있으면
        가로세로가 뒤바뀐 "회전 반영" 좌표계다. 확대/축소만 되돌리면 이 회전 반영
        좌표계 값이 나오는데, `add_rect_annot`/`insert_text`/`insert_image` 등은
        회전이 적용되기 "전"의 원본 좌표계를 기대하므로 그대로 쓰면 회전된 페이지에서
        편집 위치가 어긋난다. `page.derotation_matrix`로 한 번 더 보정해서 항상
        원본 좌표계로 돌려준다(회전 없는 페이지는 이 행렬이 항등변환이라 영향 없음).

        호출부가 이미 같은 페이지를 불러와 놨으면 `page`로 넘겨서 중복
        `load_page()`를 피할 수 있다(마우스 드래그 중 반복 호출되는 경우가 많음).
        """
        top = self.page_tops[page_index]
        inv = ~fitz.Matrix(self.zoom, self.zoom)
        displayed = fitz.Point(widget_point.x(), widget_point.y() - top) * inv
        if page is None:
            page = self.doc.load_page(page_index)
        return displayed * page.derotation_matrix

    # ---------- 그리기 ----------

    _SHADOW_LAYERS = [(10, 60), (6, 45), (3, 45), (1, 60)]  # (여백, 알파) 바깥→안쪽

    def _paint_page_shadow(self, painter: QPainter, page_rect: QRect):
        """페이지 뒤에 종이 그림자를 그린다.

        예전엔 `QGraphicsDropShadowEffect`를 캔버스 위젯 전체에 걸었는데, 이
        캔버스는 문서 전체 높이(수백만 픽셀도 가능)만큼 큰 위젯이라 효과가
        위젯 전체 크기의 오프스크린 버퍼를 만들어 블러를 계산함 — 대용량 PDF
        (예: 2000페이지)를 열면 처음 그릴 때 실측 1분 가까이 멈추는 원인이었음.
        지금은 화면에 실제로 보이는 페이지 사각형 뒤에만 겹친 반투명 사각형
        몇 겹으로 그림자를 흉내내서, 페이지 수와 무관하게 항상 가볍다.
        """
        offset = QPoint(0, 4)
        for margin, alpha in self._SHADOW_LAYERS:
            rect = page_rect.translated(offset).adjusted(-margin, -margin, margin, margin)
            painter.fillRect(rect, QColor(0, 0, 0, alpha))

    def paintEvent(self, event):
        painter = QPainter(self)
        clip = event.rect()
        # 캔버스는 문서 전체 높이만큼 큰 위젯이라(QScrollArea가 스크롤하도록),
        # 줌/문서 열기 때 setFixedSize()로 크기가 바뀌면 Qt가 "새로 넓어진
        # 영역 전체"를 dirty rect로 통째로 넘겨줄 수 있음 — event.rect()만 믿으면
        # 화면에 실제로 안 보이는 페이지까지 전부 렌더링하게 되어 지연 렌더링의
        # 의미가 없어짐. 그래서 실제로 화면(QScrollArea 뷰포트)에 보이는 영역
        # (visibleRegion())으로 한 번 더 좁혀서, 정말 눈에 보이는 페이지만 그림.
        visible = self.visibleRegion().boundingRect()
        if not visible.isEmpty():
            clip = clip.intersected(visible)
        for i, top in enumerate(self.page_tops):
            w, h = self.page_sizes[i]
            page_rect = QRect(0, int(top), w, h)
            if not page_rect.intersects(clip):
                continue
            self._paint_page_shadow(painter, page_rect)
            pm = self._ensure_page_rendered(i)
            if pm is not None:
                painter.drawPixmap(page_rect.topLeft(), pm)
            else:
                painter.fillRect(page_rect, QColor("white"))
        if self.search_highlight:
            page_idx, rect = self.search_highlight
            if 0 <= page_idx < len(self.page_tops):
                top = self.page_tops[page_idx]
                z = self.zoom
                # rect(page.search_for 결과)는 항상 원본(mediabox) 좌표라서,
                # 회전된 페이지에서는 화면표시 좌표로 먼저 옮겨야 위치가 맞다.
                page = self.doc.load_page(page_idx)
                disp = rect * page.rotation_matrix
                hl = QRectF(disp.x0 * z, top + disp.y0 * z,
                            (disp.x1 - disp.x0) * z, (disp.y1 - disp.y0) * z)
                painter.fillRect(hl, QColor(255, 165, 0, 120))
        if self._dragging:
            pen = QPen(self.color, 2, Qt.DashLine)
            painter.setPen(pen)
            if self.tool == Tool.PEN:
                for i in range(1, len(self._pen_points)):
                    painter.drawLine(self._pen_points[i - 1], self._pen_points[i])
            elif self._press_point and self._current_point:
                rect = self._widget_rect(self._press_point, self._current_point)
                if self.tool == Tool.ELLIPSE:
                    painter.drawEllipse(rect)
                else:
                    painter.drawRect(rect)
        self._paint_selection(painter)
        painter.end()

    def _paint_selection(self, painter: QPainter):
        if self._select_drag_mode == "text_select" and self._select_drag_start and self._current_point:
            rect = self._widget_rect(self._select_drag_start, self._current_point)
            painter.setPen(QPen(QColor(51, 153, 255), 1, Qt.DashLine))
            painter.setBrush(QColor(51, 153, 255, 60))
            painter.drawRect(rect)
        elif self.text_selection:
            page_idx, rect = self.text_selection
            page = self.doc.load_page(page_idx)
            quads = _word_quads_in_rect(page, rect) or [rect.quad]
            top = self.page_tops[page_idx]
            z = self.zoom
            rot = page.rotation_matrix
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(51, 153, 255, 90))
            for q in quads:
                # get_text가 돌려주는 quad도 원본(mediabox) 좌표라서, 회전된
                # 페이지에서는 화면표시 좌표로 옮긴 뒤에 그려야 위치가 맞다.
                disp = fitz.Rect(min(q.ul.x, q.ur.x, q.ll.x, q.lr.x),
                                  min(q.ul.y, q.ur.y, q.ll.y, q.lr.y),
                                  max(q.ul.x, q.ur.x, q.ll.x, q.lr.x),
                                  max(q.ul.y, q.ur.y, q.ll.y, q.lr.y)) * rot
                painter.drawRect(QRectF(disp.x0 * z, top + disp.y0 * z,
                                         (disp.x1 - disp.x0) * z,
                                         (disp.y1 - disp.y0) * z).toRect())

        annot = self.get_selected_annot()
        if annot is None:
            return
        if self._select_drag_mode:
            r = self._drag_preview_rect()
            top = self.page_tops[self.selected_page_idx]
            z = self.zoom
            rect = QRect(int(r.x0 * z), int(top + r.y0 * z),
                         int((r.x1 - r.x0) * z), int((r.y1 - r.y0) * z))
        else:
            rect = self._annot_widget_rect(annot, self.selected_page_idx)
        painter.setPen(QPen(QColor(30, 120, 220), 1.5, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect)
        painter.setPen(QPen(QColor(30, 120, 220), 1))
        painter.setBrush(QColor(255, 255, 255))
        for pt in self._handle_positions(rect).values():
            painter.drawRect(pt.x() - HANDLE_SIZE, pt.y() - HANDLE_SIZE,
                              HANDLE_SIZE * 2, HANDLE_SIZE * 2)

    @staticmethod
    def _widget_rect(p1: QPoint, p2: QPoint):
        x0, x1 = sorted((p1.x(), p2.x()))
        y0, y1 = sorted((p1.y(), p2.y()))
        return QRect(x0, y0, x1 - x0, y1 - y0)

    # ---------- 마우스/휠 이벤트 ----------

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.zoomRequested.emit(factor)
            event.accept()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if not self.doc:
            return
        if event.button() != Qt.LeftButton:
            return
        if self.tool == Tool.NONE:
            self._handle_select_press(event.pos())
            return
        page_idx = self.page_at_y(event.pos().y())
        if page_idx is None:
            return
        self._active_page_index = page_idx
        self._press_point = event.pos()
        self._current_point = event.pos()
        if self.tool == Tool.PEN:
            self._pen_points = [event.pos()]
        if self.tool in DRAG_TOOLS:
            self._dragging = True
        self.update()

    def mouseMoveEvent(self, event):
        if self.tool == Tool.NONE:
            if self._select_drag_mode:
                self._current_point = event.pos()
                self.update()
            else:
                self._update_hover_cursor(event.pos())
            return
        if not self._dragging:
            return
        self._current_point = event.pos()
        if self.tool == Tool.PEN:
            self._pen_points.append(event.pos())
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self.tool == Tool.NONE:
            if self._select_drag_mode == "text_select":
                self._current_point = event.pos()
                self._commit_text_selection()
            elif self._select_drag_mode:
                self._current_point = event.pos()
                self._commit_select_drag()
            self._select_drag_mode = None
            self._select_drag_handle = None
            self.update()
            return
        if not self.doc:
            return
        if self._press_point is None or self._active_page_index is None:
            return

        release_point = event.pos()
        page_idx = self._active_page_index
        if self.tool in CLICK_TOOLS:
            self._handle_click_tool(self._press_point, page_idx)
        elif self.tool in DRAG_TOOLS:
            self._handle_drag_tool(self._press_point, release_point, page_idx)

        self._dragging = False
        self._press_point = None
        self._current_point = None
        self._pen_points = []
        self._active_page_index = None
        self.update()

    def contextMenuEvent(self, event):
        if self.tool != Tool.NONE or not self.text_selection:
            event.ignore()
            return
        menu = QMenu(self)
        act_copy = menu.addAction(tr("copy"))
        chosen = menu.exec(event.globalPos())
        if chosen == act_copy:
            self.copy_to_clipboard()

    # ---------- 도구별 처리 ----------

    def _handle_click_tool(self, point: QPoint, page_idx: int):
        page = self.doc.load_page(page_idx)
        pdf_point = self._to_pdf_point(point, page_idx, page)

        if self.tool == Tool.NOTE:
            text, ok = QInputDialog.getMultiLineText(
                self, tr("note_title"), tr("note_label"))
            if ok and text.strip():
                self.push_undo()
                page.add_text_annot(pdf_point, text)
                self._finish_edit(page_idx)

        elif self.tool == Tool.ERASER:
            for annot in page.annots() or []:
                if annot.rect.contains(pdf_point):
                    self.push_undo()
                    page.delete_annot(annot)
                    self._finish_edit(page_idx)
                    break

    def _handle_drag_tool(self, p1: QPoint, p2: QPoint, page_idx: int):
        if p1 == p2 and self.tool not in (Tool.PEN, Tool.CAPTURE_PLACE):
            return
        page = self.doc.load_page(page_idx)
        pdf_p1 = self._to_pdf_point(p1, page_idx, page)
        pdf_p2 = self._to_pdf_point(p2, page_idx, page)
        rect = _normalized_rect(pdf_p1, pdf_p2)
        color = (self.color.redF(), self.color.greenF(), self.color.blueF())

        if self.tool == Tool.HIGHLIGHT:
            self.push_undo()
            target = _word_quads_in_rect(page, rect) or rect
            annot = page.add_highlight_annot(target)
            annot.set_colors(stroke=(1, 1, 0))
            annot.update()
            self._finish_edit(page_idx)

        elif self.tool == Tool.UNDERLINE:
            self.push_undo()
            target = _word_quads_in_rect(page, rect) or rect
            annot = page.add_underline_annot(target)
            annot.set_colors(stroke=color)
            annot.update()
            self._finish_edit(page_idx)

        elif self.tool == Tool.STRIKEOUT:
            self.push_undo()
            target = _word_quads_in_rect(page, rect) or rect
            annot = page.add_strikeout_annot(target)
            annot.set_colors(stroke=color)
            annot.update()
            self._finish_edit(page_idx)

        elif self.tool == Tool.RECT:
            self.push_undo()
            annot = page.add_rect_annot(rect)
            annot.set_colors(stroke=color)
            annot.set_border(width=1.5)
            annot.update()
            self._finish_edit(page_idx)

        elif self.tool == Tool.ELLIPSE:
            self.push_undo()
            annot = page.add_circle_annot(rect)
            annot.set_colors(stroke=color)
            annot.set_border(width=1.5)
            annot.update()
            self._finish_edit(page_idx)

        elif self.tool == Tool.PEN:
            if len(self._pen_points) < 2:
                return
            self.push_undo()
            pdf_points = [(p.x, p.y) for p in
                          (self._to_pdf_point(pt, page_idx, page) for pt in self._pen_points)]
            annot = page.add_ink_annot([pdf_points])
            annot.set_colors(stroke=color)
            annot.set_border(width=2)
            annot.update()
            self._finish_edit(page_idx)

        elif self.tool == Tool.FREETEXT:
            text, ok = QInputDialog.getMultiLineText(
                self, tr("freetext_title"), tr("freetext_label"))
            if ok and text.strip():
                self.push_undo()
                annot = page.add_freetext_annot(rect, text, fontsize=12,
                                                 text_color=(0, 0, 0),
                                                 fill_color=(1, 1, 0.75))
                annot.update()
                self._finish_edit(page_idx)

        elif self.tool == Tool.EDIT_TEXT:
            target = _snap_edit_target(page, rect)
            edit_rect = target["rect"] if target else rect
            existing = page.get_textbox(edit_rect).strip()
            text, ok = QInputDialog.getMultiLineText(
                self, tr("edit_text_title"), tr("edit_text_label"),
                text=existing)
            if ok:
                self.push_undo()
                page.add_redact_annot(edit_rect, fill=(1, 1, 1))
                page.apply_redactions()
                if text.strip():
                    if target:
                        fontname = _map_fontname(target["font"], target["flags"])
                        color = _color_int_to_rgb(target["color"])
                        if target["single_line"] and "\n" not in text:
                            max_width = _remaining_width(
                                page, target["origin"], page.rotation) - 10
                            _insert_text_fit(page, target["origin"], text,
                                              target["size"], fontname, color, max_width,
                                              rotate=page.rotation)
                        else:
                            _fit_textbox(page, edit_rect, text,
                                         start_size=target["size"],
                                         fontname=fontname, color=color,
                                         rotate=page.rotation)
                    else:
                        _fit_textbox(page, edit_rect, text, rotate=page.rotation)
                self._finish_edit(page_idx)

        elif self.tool == Tool.CAPTURE_PLACE:
            self._place_captured_image(p1, p2, page_idx)

    def _place_captured_image(self, p1: QPoint, p2: QPoint, page_idx: int):
        pixmap = self._pending_capture_pixmap
        if pixmap is None:
            return
        page = self.doc.load_page(page_idx)

        # insert_image()는 이미지를 원본(mediabox) 좌표계에 그대로 박아넣는데,
        # 페이지 자체의 /Rotate가 그 위에 다시 적용되어 화면에 보이므로, 아무
        # 보정 없이 넣으면 캡처한 화면이 페이지 회전만큼 돌아간 채로 보인다.
        # 캡처한 그대로(화면에서 본 방향)로 보이게 하려면, 페이지 회전과
        # 반대 방향(시계방향 (360-rotation)도)으로 미리 돌려서 넣어야 한다.
        rotation = page.rotation % 360
        if rotation:
            pixmap = pixmap.transformed(QTransform().rotate((360 - rotation) % 360))

        if p1 == p2:
            # 그냥 클릭만 했으면, 캡처 원본 픽셀 크기를 화면 72dpi 기준 PDF 포인트로
            # 환산해 그 자리에 자연스러운 크기로 놓는다(드래그하면 원하는 크기로).
            origin = self._to_pdf_point(p1, page_idx, page)
            w = pixmap.width() * 72 / 96
            h = pixmap.height() * 72 / 96
            rect = fitz.Rect(origin.x, origin.y, origin.x + w, origin.y + h)
        else:
            pdf_p1 = self._to_pdf_point(p1, page_idx, page)
            pdf_p2 = self._to_pdf_point(p2, page_idx, page)
            rect = _normalized_rect(pdf_p1, pdf_p2)

        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        pixmap.save(buf, "PNG")
        png_bytes = bytes(buf.data())
        buf.close()

        self.push_undo()
        page.insert_image(rect, stream=png_bytes)
        self._pending_capture_pixmap = None
        tool_to_restore = self._tool_before_capture
        self._finish_edit(page_idx)
        self.set_tool(tool_to_restore)
        self.captureInserted.emit()

    def _finish_edit(self, page_idx: int):
        self.render_single_page(page_idx)
        self.documentChanged.emit()
        self.pageContentChanged.emit(page_idx)

    # ---------- 실행취소/다시실행 ----------

    def push_undo(self):
        if not self.doc:
            return
        try:
            data = self.doc.tobytes()
        except Exception:
            return
        self._undo_stack.append((data, self.page_index))
        if len(self._undo_stack) > self._undo_limit:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self.undoAvailable.emit(True)
        self.redoAvailable.emit(False)

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def undo(self):
        if not self._undo_stack:
            return
        self.clear_selection()
        self._redo_stack.append((self.doc.tobytes(), self.page_index))
        data, page_index = self._undo_stack.pop()
        self.doc = fitz.open(stream=data, filetype="pdf")
        self.page_index = min(page_index, self.doc.page_count - 1)
        self.render_all_pages()
        self.pageChanged.emit()
        self.documentChanged.emit()
        self.undoAvailable.emit(self.can_undo())
        self.redoAvailable.emit(self.can_redo())

    def redo(self):
        if not self._redo_stack:
            return
        self.clear_selection()
        self._undo_stack.append((self.doc.tobytes(), self.page_index))
        if len(self._undo_stack) > self._undo_limit:
            self._undo_stack.pop(0)
        data, page_index = self._redo_stack.pop()
        self.doc = fitz.open(stream=data, filetype="pdf")
        self.page_index = min(page_index, self.doc.page_count - 1)
        self.render_all_pages()
        self.pageChanged.emit()
        self.documentChanged.emit()
        self.undoAvailable.emit(self.can_undo())
        self.redoAvailable.emit(self.can_redo())
