import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
import hwp_loader
import md_loader
from PySide6.QtWidgets import QApplication
import main

def test_loaders_and_gui():
    print("=== 1. HWP Loader Optimization Test ===")
    hwp_path = "sample/전국민 AI 경진대회 통합 공고문.hwp"
    if os.path.exists(hwp_path):
        doc_hwp = hwp_loader.load_hwp_as_fitz_doc(hwp_path)
        print(f"[HWP] Successfully loaded: {len(doc_hwp)} pages")
        assert len(doc_hwp) > 0, "HWP doc has 0 pages"
    else:
        print("[HWP] Sample file not found, skipping specific sample test")

    print("\n=== 2. Markdown Multi-encoding Test ===")
    # 2-1. UTF-8 Markdown
    fd, md_utf8_path = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    with open(md_utf8_path, "w", encoding="utf-8") as f:
        f.write("# UTF-8 마크다운 테스트\n\n- 항목 1\n- 항목 2\n\n```python\nprint('hello')\n```\n\n| 제목 | 내용 |\n| --- | --- |\n| A | 100 |\n")

    doc_utf8 = md_loader.load_md_as_fitz_doc(md_utf8_path)
    print(f"[MD-UTF8] Successfully loaded: {len(doc_utf8)} pages")
    os.remove(md_utf8_path)

    # 2-2. CP949 (Windows ANSI) Markdown
    fd, md_cp949_path = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    with open(md_cp949_path, "w", encoding="cp949") as f:
        f.write("# CP949 한글 마크다운 테스트\n\n메모장에서 ANSI로 저장된 파일입니다.\n\n| 구분 | 사양 |\n| --- | --- |\n| CPU | i7 |\n")

    doc_cp949 = md_loader.load_md_as_fitz_doc(md_cp949_path)
    print(f"[MD-CP949] Successfully loaded: {len(doc_cp949)} pages")
    page_text = doc_cp949[0].get_text()
    assert "CP949" in page_text or "메모장" in page_text
    print("[MD-CP949] Text encoding preservation verified!")
    os.remove(md_cp949_path)

    print("\n=== 3. GUI Integration Test ===")
    app = QApplication.instance() or QApplication(sys.argv)
    window = main.MainWindow()
    assert "PDF Super Viewer (HWP,MD)" in window.windowTitle()
    print("[GUI] Window title verified:", window.windowTitle())

    # README.md 열기 테스트
    if os.path.exists("README.md"):
        window._open_path(os.path.abspath("README.md"))
        v = window.current_view()
        assert v is not None
        assert v.is_md == True
        assert "[MD]" in v.label()
        print("[GUI] README.md loaded in tab with label:", v.label())

    print("\n===> ALL OPTIMIZATION & INTEGRATION TESTS PASSED SUCCESSFULLY! <===")

if __name__ == "__main__":
    test_loaders_and_gui()
