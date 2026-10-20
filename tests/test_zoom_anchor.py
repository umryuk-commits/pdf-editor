import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint
import fitz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main

def test_zoom_anchor_preservation():
    app = QApplication.instance() or QApplication(sys.argv)
    win = main.MainWindow()
    win.resize(1000, 800)
    win.show()

    # 10페이지 분량 문서 생성
    doc = fitz.open()
    for i in range(10):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), f"Page {i+1}", fontsize=30)

    view = main.DocumentView(win)
    win.tabs.addTab(view, "ZoomTest")
    win.tabs.setCurrentIndex(0)
    view.canvas.load_document(doc)
    app.processEvents()

    # 1. 5페이지 (인덱스 4)로 이동 확인
    win.scroll_to_page(4)
    app.processEvents()
    assert view.canvas.page_index == 4, f"Expected page_index 4, got {view.canvas.page_index}"
    assert win._current_center_page() == 4, f"Expected center page 4, got {win._current_center_page()}"

    # 2. 확대 (+) 테스트: 5페이지 유지 확인
    win.set_zoom(view.canvas.zoom * 1.25)
    app.processEvents()
    assert win._current_center_page() == 4, f"Expected center page 4 after zoom in, got {win._current_center_page()}"
    assert view.canvas.page_index == 4, f"Expected page_index 4 after zoom in, got {view.canvas.page_index}"

    # 3. 축소 (-) 테스트: 5페이지 유지 확인
    win.set_zoom(view.canvas.zoom / 1.25)
    app.processEvents()
    assert win._current_center_page() == 4, f"Expected center page 4 after zoom out, got {win._current_center_page()}"
    assert view.canvas.page_index == 4, f"Expected page_index 4 after zoom out, got {view.canvas.page_index}"

    # 4. 마우스 위치 기준 Ctrl+휠 확대/축소 시뮬레이션: 5페이지 유지 확인
    page_5_top = view.canvas.page_tops[4]
    mouse_pt = QPoint(200, int(page_5_top + 150))
    view.canvas.zoomRequested.emit(1.15, mouse_pt)
    app.processEvents()
    assert win._current_center_page() == 4, f"Expected center page 4 after wheel zoom in, got {win._current_center_page()}"

    view.canvas.zoomRequested.emit(1 / 1.15, mouse_pt)
    app.processEvents()
    assert win._current_center_page() == 4, f"Expected center page 4 after wheel zoom out, got {win._current_center_page()}"

    print(">>> test_zoom_anchor_preservation PASSED successfully! <<<")

if __name__ == "__main__":
    test_zoom_anchor_preservation()
