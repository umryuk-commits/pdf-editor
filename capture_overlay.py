"""데스크톱의 임의 사각형 영역을 캡처하는 반투명 오버레이(Windows 캡처 도구 대체).

여러 모니터에 걸쳐 있는 가상 데스크톱 전체를 덮는 진짜 반투명(`WA_TranslucentBackground`)
프레임리스 창을 띄우고, 드래그 중인 사각형만 뚫어서 그 안으로 실제 데스크톱이
그대로 비쳐 보이게 한다(구멍 안쪽은 OS 컴포지터가 그려주므로 우리가 화면을 따로
복사해서 그릴 필요가 없다 — 가볍고 코드도 단순함).

**PDF 편집기 창은 숨기지 않는다** — 숨기는 건 이 오버레이 자신뿐이고, 그것도
드래그가 끝나 실제로 화면을 긁어갈 그 순간(`mouseReleaseEvent`)에 아주 잠깐뿐이다.
그래야 오버레이 자신의 반투명 틴트/테두리가 캡처 결과에 섞여 들어가지 않는다.
"""
from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

# 오버레이를 숨긴 뒤 실제로 화면을 긁어가기까지 기다리는 시간(ms) — 너무 짧으면
# OS가 아직 창을 다 지우지 못해 오버레이 잔상이 캡처에 섞여 들어갈 수 있다.
_HIDE_TO_GRAB_DELAY_MS = 100


class CaptureOverlay(QWidget):
    """captured(QPixmap) 또는 cancelled()를 emit하고 스스로 닫히는 1회용 오버레이."""

    captured = Signal(QPixmap)
    cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self._start: QPoint | None = None
        self._current: QPoint | None = None

        geo = QRect()
        for screen in QGuiApplication.screens():
            geo = geo.united(screen.geometry())
        self._virtual_origin = geo.topLeft()
        self.setGeometry(geo)

    def start(self):
        self.show()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            self.cancelled.emit()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start = event.globalPos()
            self._current = self._start
            self.update()

    def mouseMoveEvent(self, event):
        if self._start is not None:
            self._current = event.globalPos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self._start is None:
            return
        rect = QRect(self._start, event.globalPos()).normalized()
        if rect.width() < 3 or rect.height() < 3:
            self.close()
            self.cancelled.emit()
            return
        # 오버레이 자신을 먼저 숨기고, 화면이 실제로 지워질 시간을 잠깐 준 다음에
        # 긁어간다 — 그래야 우리가 그린 반투명 틴트/테두리가 캡처 결과에 안 섞인다.
        self.hide()
        QTimer.singleShot(_HIDE_TO_GRAB_DELAY_MS, lambda: self._finish_capture(rect))

    def _finish_capture(self, rect: QRect):
        pixmap = self._grab_desktop(rect)
        self.close()
        self.captured.emit(pixmap)

    @staticmethod
    def _grab_desktop(rect: QRect) -> QPixmap:
        """가상 데스크톱 좌표 rect에 해당하는 화면 영역을 모니터별로 이어붙여 캡처."""
        result = QPixmap(rect.size())
        result.fill(Qt.black)
        painter = QPainter(result)
        for screen in QGuiApplication.screens():
            screen_geo = screen.geometry()
            inter = screen_geo.intersected(rect)
            if inter.isEmpty():
                continue
            local = inter.translated(-screen_geo.topLeft())
            shot = screen.grabWindow(0, local.x(), local.y(), local.width(), local.height())
            painter.drawPixmap(inter.topLeft() - rect.topLeft(), shot)
        painter.end()
        return result

    def paintEvent(self, event):
        # 창 전체를 반투명 검은색으로 덮고, 드래그 중인 사각형만 완전히 뚫는다
        # (`WA_TranslucentBackground` 덕분에 뚫린 자리로 실제 데스크톱이 실시간으로
        # 그대로 비쳐 보임 — 우리가 화면을 복사해서 다시 그릴 필요가 없어 가볍다).
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        if self._start is not None and self._current is not None:
            local_rect = QRect(
                self._start - self._virtual_origin,
                self._current - self._virtual_origin,
            ).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(local_rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(51, 153, 255), 2))
            painter.drawRect(local_rect)
        painter.end()
