"""아주 가벼운 다국어(한국어/영어) 지원 모듈.

STRINGS[언어코드][키] = 문자열. tr(key)가 현재 언어의 문자열을 돌려준다.
"""

STRINGS = {
    "ko": {
        "app_title": "PDF 편집기",
        "menu_file": "파일",
        "menu_edit": "편집",
        "menu_page": "페이지",
        "menu_view": "보기",
        "menu_language": "언어 Language",
        "menu_help": "도움말",

        "open": "열기...",
        "save": "저장",
        "save_as": "다른 이름으로 저장...",
        "print": "인쇄...",
        "print_preview_title": "인쇄 미리보기",
        "exit": "종료",

        "undo": "실행취소",
        "redo": "다시 실행",
        "find": "찾기...",
        "copy": "복사",

        "insert_page": "빈 페이지 삽입",
        "delete_page": "현재 페이지 삭제",
        "rotate_page": "현재 페이지 회전 (90°)",

        "zoom_in": "확대",
        "zoom_out": "축소",
        "zoom_reset": "원래 크기",
        "fit_width": "폭 맞춤",
        "fit_page": "화면 맞춤",
        "toggle_thumbnails": "페이지 목록 보이기/숨기기",

        "about": "정보...",

        "tool_none": "선택",
        "tool_highlight": "하이라이트",
        "tool_underline": "밑줄",
        "tool_strikeout": "취소선",
        "tool_note": "노트",
        "tool_freetext": "텍스트 박스",
        "tool_pen": "펜",
        "tool_rect": "사각형",
        "tool_ellipse": "원",
        "tool_eraser": "지우개",
        "tool_edit_text": "텍스트 수정",

        "color": "색상",
        "prev_page": "< 이전",
        "next_page": "다음 >",

        "status_ready": "PDF 파일을 열어주세요. (파일을 끌어다 놓아도 됩니다)",
        "status_opened": "열림: {path}",
        "status_saved": "저장됨: {path}",
        "status_tool": "도구: {tool}",
        "status_not_found": "'{text}'을 찾을 수 없습니다.",
        "status_copied": "복사했습니다.",

        "dialog_open_pdf": "PDF 열기",
        "dialog_save_as": "다른 이름으로 저장",
        "filter_pdf": "PDF 파일 (*.pdf)",
        "color_dialog_title": "색상 선택",

        "open_failed_title": "열기 실패",
        "open_failed_msg": "파일을 열 수 없습니다:\n{exc}",
        "save_failed_title": "저장 실패",
        "save_failed_msg": "저장 중 오류가 발생했습니다:\n{exc}",
        "print_failed_title": "인쇄 실패",
        "print_failed_msg": "인쇄 중 오류가 발생했습니다:\n{exc}",

        "cancel": "취소",
        "printer_label": "프린터",
        "orientation_label": "인쇄 방향",
        "orientation_portrait": "세로",
        "orientation_landscape": "가로",
        "copies_label": "인쇄 매수",
        "page_range_label": "페이지",
        "page_range_all": "모든 페이지",
        "page_range_current": "현재 페이지",

        "delete_impossible_title": "삭제 불가",
        "delete_impossible_msg": "마지막 남은 페이지는 삭제할 수 없습니다.",
        "delete_page_title": "페이지 삭제",
        "delete_page_msg": "{n}번째 페이지를 삭제할까요?",

        "exit_title": "종료",
        "exit_msg": "저장하지 않은 변경사항이 있습니다. 그래도 종료할까요?",

        "search_placeholder": "찾을 내용 입력 후 Enter",
        "search_label": "찾기:",
        "search_prev": "◀ 이전",
        "search_next": "다음 ▶",

        "thumb_dock_title": "페이지",
        "page_indicator": "페이지 {current} / {total}",
        "untitled": "제목 없음",
        "close_tab": "탭 닫기",

        "note_title": "노트 추가",
        "note_label": "노트 내용을 입력하세요:",
        "freetext_title": "텍스트 박스 추가",
        "freetext_label": "표시할 텍스트를 입력하세요:",
        "edit_text_title": "텍스트 수정",
        "edit_text_label": "선택한 영역의 텍스트를 수정하세요 (기존 텍스트는 삭제됩니다):",

        "lang_changed": "언어가 변경되었습니다. 프로그램을 다시 시작하면 적용됩니다.",

        "about_designed_by": "Designed by {name}",
    },
    "en": {
        "app_title": "PDF Editor",
        "menu_file": "File",
        "menu_edit": "Edit",
        "menu_page": "Page",
        "menu_view": "View",
        "menu_language": "언어 Language",
        "menu_help": "Help",

        "open": "Open...",
        "save": "Save",
        "save_as": "Save As...",
        "print": "Print...",
        "print_preview_title": "Print Preview",
        "exit": "Exit",

        "undo": "Undo",
        "redo": "Redo",
        "find": "Find...",
        "copy": "Copy",

        "insert_page": "Insert Blank Page",
        "delete_page": "Delete Current Page",
        "rotate_page": "Rotate Current Page (90°)",

        "zoom_in": "Zoom In",
        "zoom_out": "Zoom Out",
        "zoom_reset": "Actual Size",
        "fit_width": "Fit Width",
        "fit_page": "Fit Page",
        "toggle_thumbnails": "Show/Hide Page List",

        "about": "About...",

        "tool_none": "Select",
        "tool_highlight": "Highlight",
        "tool_underline": "Underline",
        "tool_strikeout": "Strikeout",
        "tool_note": "Note",
        "tool_freetext": "Text Box",
        "tool_pen": "Pen",
        "tool_rect": "Rectangle",
        "tool_ellipse": "Ellipse",
        "tool_eraser": "Eraser",
        "tool_edit_text": "Edit Text",

        "color": "Color",
        "prev_page": "< Prev",
        "next_page": "Next >",

        "status_ready": "Open a PDF file. (You can also drag & drop one here.)",
        "status_opened": "Opened: {path}",
        "status_saved": "Saved: {path}",
        "status_tool": "Tool: {tool}",
        "status_not_found": "'{text}' not found.",
        "status_copied": "Copied.",

        "dialog_open_pdf": "Open PDF",
        "dialog_save_as": "Save As",
        "filter_pdf": "PDF Files (*.pdf)",
        "color_dialog_title": "Select Color",

        "open_failed_title": "Open Failed",
        "open_failed_msg": "Could not open file:\n{exc}",
        "save_failed_title": "Save Failed",
        "save_failed_msg": "An error occurred while saving:\n{exc}",
        "print_failed_title": "Print Failed",
        "print_failed_msg": "An error occurred while printing:\n{exc}",

        "cancel": "Cancel",
        "printer_label": "Printer",
        "orientation_label": "Orientation",
        "orientation_portrait": "Portrait",
        "orientation_landscape": "Landscape",
        "copies_label": "Copies",
        "page_range_label": "Pages",
        "page_range_all": "All Pages",
        "page_range_current": "Current Page",

        "delete_impossible_title": "Cannot Delete",
        "delete_impossible_msg": "The last remaining page cannot be deleted.",
        "delete_page_title": "Delete Page",
        "delete_page_msg": "Delete page {n}?",

        "exit_title": "Exit",
        "exit_msg": "There are unsaved changes. Exit anyway?",

        "search_placeholder": "Type text and press Enter",
        "search_label": "Find:",
        "search_prev": "◀ Prev",
        "search_next": "Next ▶",

        "thumb_dock_title": "Pages",
        "page_indicator": "Page {current} / {total}",
        "untitled": "Untitled",
        "close_tab": "Close Tab",

        "note_title": "Add Note",
        "note_label": "Enter note content:",
        "freetext_title": "Add Text Box",
        "freetext_label": "Enter text to display:",
        "edit_text_title": "Edit Text",
        "edit_text_label": "Edit the text in the selected area (the original text will be removed):",

        "lang_changed": "Language changed. Restart the app to apply it.",

        "about_designed_by": "Designed by {name}",
    },
}

DEFAULT_LANG = "ko"
_current_lang = DEFAULT_LANG


def set_language(lang: str):
    global _current_lang
    _current_lang = lang if lang in STRINGS else DEFAULT_LANG


def get_language() -> str:
    return _current_lang


def available_languages() -> list[str]:
    return list(STRINGS.keys())


def tr(key: str, **kwargs) -> str:
    text = STRINGS.get(_current_lang, STRINGS[DEFAULT_LANG]).get(
        key, STRINGS[DEFAULT_LANG].get(key, key))
    return text.format(**kwargs) if kwargs else text
