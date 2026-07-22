"""툴바 아이콘. 외부 아이콘 파일/패키지 없이 QPainter로 직접 그려서 QIcon으로 만든다.

전부 20x20 캔버스에 같은 굵기(1.6px)의 짙은 회색 선으로 그려서 톤을 통일한다.
색상 도구(펜/사각형/원/하이라이트/밑줄/취소선)의 아이콘 자체는 항상 이 중립색이고,
실제 선택된 색상은 도구 선택 시 나타나는 색상 팔레트 줄에서 별도로 보여준다
(아이콘에 색을 입히면 방금 고른 색과 헷갈릴 수 있어 일부러 분리함).
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
)

_INK = "#4a4a4a"
_SIZE = 20


def _new_painter(size: int = _SIZE) -> tuple[QPixmap, QPainter]:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(_INK), 1.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    return pix, p


def _finish(pix: QPixmap, p: QPainter) -> QIcon:
    p.end()
    return QIcon(pix)




def icon_open() -> QIcon:
    pix, p = _new_painter()
    p.drawLine(QPointF(3, 6), QPointF(8, 6))
    p.drawLine(QPointF(8, 6), QPointF(10, 8))
    path = QPolygonF([QPointF(3, 6), QPointF(3, 16), QPointF(17, 16),
                       QPointF(17, 8), QPointF(10, 8)])
    p.drawPolygon(path)
    return _finish(pix, p)


def icon_save() -> QIcon:
    pix, p = _new_painter()
    p.drawRoundedRect(QRectF(3, 3, 14, 14), 1.5, 1.5)
    p.drawRect(QRectF(6, 3, 8, 5))
    p.drawRect(QRectF(6, 11, 8, 6))
    return _finish(pix, p)


def icon_print() -> QIcon:
    pix, p = _new_painter()
    p.drawRect(QRectF(5, 7, 10, 6))
    p.drawRect(QRectF(6, 3, 8, 4))
    p.drawRect(QRectF(7, 13, 6, 4))
    return _finish(pix, p)


def icon_undo() -> QIcon:
    pix, p = _new_painter()
    path = QPainterPath()
    path.moveTo(15, 14)
    path.arcTo(QRectF(5, 6, 10, 8), 0, 200)
    p.drawPath(path)
    arrow = QPolygonF([QPointF(5, 6), QPointF(9, 5), QPointF(7, 10)])
    p.setBrush(QBrush(p.pen().color()))
    p.drawPolygon(arrow)
    return _finish(pix, p)


def icon_redo() -> QIcon:
    pix, p = _new_painter()
    path = QPainterPath()
    path.moveTo(5, 14)
    path.arcTo(QRectF(5, 6, 10, 8), 180, 200)
    p.drawPath(path)
    arrow = QPolygonF([QPointF(15, 6), QPointF(11, 5), QPointF(13, 10)])
    p.setBrush(QBrush(p.pen().color()))
    p.drawPolygon(arrow)
    return _finish(pix, p)


def icon_find() -> QIcon:
    pix, p = _new_painter()
    p.drawEllipse(QRectF(4, 4, 9, 9))
    p.drawLine(QPointF(12, 12), QPointF(16, 16))
    return _finish(pix, p)


def icon_capture() -> QIcon:
    pix, p = _new_painter()
    corners = [
        ((3, 7), (3, 3), (7, 3)),
        ((13, 3), (17, 3), (17, 7)),
        ((17, 13), (17, 17), (13, 17)),
        ((7, 17), (3, 17), (3, 13)),
    ]
    for a, b, c in corners:
        p.drawLine(QPointF(*a), QPointF(*b))
        p.drawLine(QPointF(*b), QPointF(*c))
    return _finish(pix, p)


def icon_select() -> QIcon:
    pix, p = _new_painter()
    p.setBrush(QBrush(p.pen().color()))
    arrow = QPolygonF([
        QPointF(4, 3), QPointF(4, 16), QPointF(8, 12.5),
        QPointF(10.5, 17.5), QPointF(12.5, 16.5), QPointF(10, 11.5),
        QPointF(15, 11),
    ])
    p.drawPolygon(arrow)
    return _finish(pix, p)


def icon_highlight() -> QIcon:
    pix, p = _new_painter()
    p.setBrush(QBrush(p.pen().color()))
    body = QPolygonF([QPointF(6, 3), QPointF(10, 3), QPointF(15, 12),
                      QPointF(11, 14), QPointF(6, 6)])
    p.drawPolygon(body)
    p.setBrush(QBrush(Qt.NoBrush))
    p.drawLine(QPointF(4, 17), QPointF(13, 17))
    return _finish(pix, p)


def icon_underline() -> QIcon:
    # 글자 대신 각진 U자 모양(세로선 2개 + 아래 가로선)을 직접 그린다 — 이 크기의
    # 아이콘에서는 폰트로 그린 U/S 글자가 안티앨리어싱 때문에 뭉개져 잘 안 보였음.
    pix, p = _new_painter()
    p.drawLine(QPointF(6, 4), QPointF(6, 11))
    p.drawLine(QPointF(14, 4), QPointF(14, 11))
    p.drawLine(QPointF(6, 11), QPointF(14, 11))
    p.drawLine(QPointF(4, 16), QPointF(16, 16))
    return _finish(pix, p)


def icon_strikeout() -> QIcon:
    # 텍스트 줄 3개 + 가운데를 가로지르는 취소선 한 줄.
    pix, p = _new_painter()
    p.drawLine(QPointF(4, 6), QPointF(15, 6))
    p.drawLine(QPointF(4, 14), QPointF(12, 14))
    p.drawLine(QPointF(3, 10), QPointF(17, 10))
    return _finish(pix, p)


def icon_note() -> QIcon:
    pix, p = _new_painter()
    path = QPolygonF([QPointF(3, 3), QPointF(17, 3), QPointF(17, 13),
                      QPointF(13, 17), QPointF(3, 17)])
    p.drawPolygon(path)
    p.drawLine(QPointF(13, 13), QPointF(13, 17))
    p.drawLine(QPointF(13, 13), QPointF(17, 13))
    p.drawLine(QPointF(6, 7), QPointF(14, 7))
    p.drawLine(QPointF(6, 10.5), QPointF(11, 10.5))
    return _finish(pix, p)


def icon_freetext() -> QIcon:
    pix, p = _new_painter()
    pen = p.pen()
    pen.setStyle(Qt.DashLine)
    p.setPen(pen)
    p.drawRect(QRectF(3, 3, 14, 14))
    solid = QPen(QColor(_INK), 1.8)
    solid.setCapStyle(Qt.RoundCap)
    p.setPen(solid)
    p.drawLine(QPointF(7, 7), QPointF(13, 7))
    p.drawLine(QPointF(10, 7), QPointF(10, 14))
    return _finish(pix, p)


def icon_pen() -> QIcon:
    pix, p = _new_painter()
    p.drawLine(QPointF(4, 16), QPointF(13, 7))
    p.setBrush(QBrush(p.pen().color()))
    p.drawEllipse(QRectF(12, 3, 5, 5))
    tip = QPolygonF([QPointF(3, 17), QPointF(4, 13), QPointF(7, 16)])
    p.drawPolygon(tip)
    return _finish(pix, p)


def icon_rect() -> QIcon:
    pix, p = _new_painter()
    p.drawRect(QRectF(3.5, 5, 13, 10))
    return _finish(pix, p)


def icon_ellipse() -> QIcon:
    pix, p = _new_painter()
    p.drawEllipse(QRectF(3, 4, 14, 12))
    return _finish(pix, p)


def icon_eraser() -> QIcon:
    pix, p = _new_painter()
    # 흰색으로 채우면 밝은 툴바 배경에 묻혀 안 보이므로 옅은 회색으로 채운다.
    p.setBrush(QBrush(QColor("#d8d8d8")))
    body = QPolygonF([QPointF(5, 12), QPointF(11, 4), QPointF(16, 8),
                      QPointF(10, 17), QPointF(4, 17)])
    p.drawPolygon(body)
    p.drawLine(QPointF(8, 17), QPointF(14, 11))
    return _finish(pix, p)


def swatch_icon(color) -> QIcon:
    """색상 팔레트 줄에 쓰이는 단색 사각형 스와치(선택된 색을 그대로 보여줌)."""
    pix = QPixmap(_SIZE, _SIZE)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(color))
    p.setPen(QPen(QColor(0, 0, 0, 90), 1))
    p.drawRoundedRect(QRectF(2, 2, 16, 16), 3, 3)
    p.end()
    return QIcon(pix)


def icon_palette() -> QIcon:
    """"더보기..." 버튼용 팔레트 아이콘(작은 색 점 여러 개)."""
    pix, p = _new_painter()
    dots = [(QColor("#e04b4b"), 6, 5), (QColor("#4ba0e0"), 14, 6),
            (QColor("#e0c04b"), 5, 14), (QColor("#4be07a"), 14, 14)]
    p.setPen(Qt.NoPen)
    for color, x, y in dots:
        p.setBrush(QBrush(color))
        p.drawEllipse(QPointF(x, y), 3.2, 3.2)
    return _finish(pix, p)


def icon_edit_text() -> QIcon:
    # "T" 글자(직접 그린 두 선) + 오른쪽 아래에 작은 연필 표시로 "수정"을 나타냄.
    pix, p = _new_painter()
    p.drawLine(QPointF(3, 4), QPointF(11, 4))
    p.drawLine(QPointF(7, 4), QPointF(7, 13))
    p.setBrush(QBrush(p.pen().color()))
    tip = QPolygonF([QPointF(12, 17), QPointF(13, 13), QPointF(17, 17)])
    p.drawPolygon(tip)
    return _finish(pix, p)
