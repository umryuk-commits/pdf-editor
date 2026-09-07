import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main

def run_test():
    app = QApplication.instance() or QApplication(sys.argv)
    window = main.MainWindow()

    hwpx_path = os.path.abspath("sample/test_sample.hwpx")
    hwp_path = os.path.abspath("sample/test_sample.hwp")

    print("[GUI Test] Opening HWPX file:", hwpx_path)
    window._open_path(hwpx_path)
    assert window.tabs.count() == 1, f"Expected 1 tab, got {window.tabs.count()}"
    v1 = window.tabs.widget(0)
    assert v1.is_hwp is True, "Expected is_hwp to be True for HWPX"
    assert "[HWP]" in window.tabs.tabText(0), "Tab text should include [HWP]"
    assert v1.canvas.doc is not None, "Document should not be None"
    print(f"[GUI Test] HWPX opened successfully. Page count: {v1.canvas.doc.page_count}")

    print("[GUI Test] Opening HWP 5.0 file:", hwp_path)
    window._open_path(hwp_path)
    assert window.tabs.count() == 2, f"Expected 2 tabs, got {window.tabs.count()}"
    v2 = window.tabs.widget(1)
    assert v2.is_hwp is True, "Expected is_hwp to be True for HWP 5.0"
    assert v2.canvas.doc is not None, "Document should not be None"
    print(f"[GUI Test] HWP 5.0 opened successfully. Page count: {v2.canvas.doc.page_count}")

    # 검색 테스트
    window.search_input.setText("바이너리")
    window.find_next()
    assert len(v2.canvas.search_matches) > 0, "Should find '바이너리' in HWP document"
    print(f"[GUI Test] Search in HWP document verified. Matches found: {len(v2.canvas.search_matches)}")

    # 탭 전환 테스트
    window.tabs.setCurrentIndex(0)
    assert window.current_view() is v1
    print("[GUI Test] Tab switching verified.")

    # PDF 저장 유도 테스트 (is_hwp일 때 save_file이 save_file_as로 유도되는지)
    # 직접 save_to 테스트
    test_pdf_out = os.path.abspath("sample/hwpx_exported.pdf")
    save_ok = window._save_to(test_pdf_out)
    assert save_ok is True, "Failed to save HWP as PDF"
    assert os.path.exists(test_pdf_out), "Exported PDF does not exist"
    print(f"[GUI Test] HWP -> PDF export verified. Size: {os.path.getsize(test_pdf_out)} bytes")

    print(">>> ALL GUI INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")
    QTimer.singleShot(100, app.quit)

if __name__ == "__main__":
    run_test()
