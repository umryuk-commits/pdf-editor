"""아주 가벼운 다국어(한국어/영어) 지원 모듈.

STRINGS[언어코드][키] = 문자열. tr(key)가 현재 언어의 문자열을 돌려준다.
"""

STRINGS = {
    "ko": {
        "app_title": "PDF Super Viewer (HWP,MD)",
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
        "capture": "캡처...",

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
        "more_colors": "더보기...",
        "prev_page": "< 이전",
        "next_page": "다음 >",

        "status_ready": "PDF, 한글(HWP), 마크다운(MD) 문서를 열어주세요. (파일을 끌어다 놓아도 됩니다)",
        "status_opened": "열림: {path}",
        "status_saved": "저장됨: {path}",
        "status_tool": "도구: {tool}",
        "status_not_found": "'{text}'을 찾을 수 없습니다.",
        "status_copied": "복사했습니다.",
        "status_capture_place": "캡처한 내용을 놓을 위치를 페이지 위에서 클릭하거나 드래그로 크기를 정하세요. (Esc: 취소)",
        "status_capture_cancelled": "캡처를 취소했습니다.",
        "status_capture_placed": "캡처한 내용을 삽입했습니다.",

        "dialog_open_pdf": "문서 열기",
        "dialog_save_as": "다른 이름으로 저장",
        "filter_open": "모든 지원 문서 (*.pdf *.hwp *.hwpx *.md *.markdown);;PDF 파일 (*.pdf);;한글 문서 (*.hwp *.hwpx);;마크다운 (*.md *.markdown);;모든 파일 (*.*)",
        "filter_pdf": "PDF 파일 (*.pdf)",
        "hwp_save_notice": "한글(HWP) 문서는 원본을 보존하기 위해 PDF 파일로 저장됩니다.",
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
        "app_title": "PDF Super Viewer (HWP,MD)",
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
        "capture": "Capture...",

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
        "more_colors": "More...",
        "prev_page": "< Prev",
        "next_page": "Next >",

        "status_ready": "Open a PDF, HWP, or Markdown file. (You can also drag & drop one here.)",
        "status_opened": "Opened: {path}",
        "status_saved": "Saved: {path}",
        "status_tool": "Tool: {tool}",
        "status_not_found": "'{text}' not found.",
        "status_copied": "Copied.",
        "status_capture_place": "Click or drag on the page to place and size the capture. (Esc: cancel)",
        "status_capture_cancelled": "Screen capture cancelled.",
        "status_capture_placed": "Capture inserted.",

        "dialog_open_pdf": "Open Document",
        "dialog_save_as": "Save As",
        "filter_open": "All Supported Documents (*.pdf *.hwp *.hwpx *.md *.markdown);;PDF Files (*.pdf);;HWP Documents (*.hwp *.hwpx);;Markdown (*.md *.markdown);;All Files (*.*)",
        "filter_pdf": "PDF Files (*.pdf)",
        "hwp_save_notice": "HWP documents are saved as PDF files to preserve the original document.",
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
    "zh": {
        "app_title": "PDF Super Viewer (HWP,MD)",
        "menu_file": "文件",
        "menu_edit": "编辑",
        "menu_page": "页面",
        "menu_view": "查看",
        "menu_language": "语言 Language",
        "menu_help": "帮助",

        "open": "打开...",
        "save": "保存",
        "save_as": "另存为...",
        "print": "打印...",
        "print_preview_title": "打印预览",
        "exit": "退出",

        "undo": "撤销",
        "redo": "重做",
        "find": "查找...",
        "copy": "复制",
        "capture": "截图...",

        "insert_page": "插入空白页",
        "delete_page": "删除当前页",
        "rotate_page": "旋转当前页 (90°)",

        "zoom_in": "放大",
        "zoom_out": "缩小",
        "zoom_reset": "实际大小",
        "fit_width": "适合宽度",
        "fit_page": "适合页面",
        "toggle_thumbnails": "显示/隐藏页面列表",

        "about": "关于...",

        "tool_none": "选择",
        "tool_highlight": "高亮",
        "tool_underline": "下划线",
        "tool_strikeout": "删除线",
        "tool_note": "批注",
        "tool_freetext": "文本框",
        "tool_pen": "画笔",
        "tool_rect": "矩形",
        "tool_ellipse": "椭圆",
        "tool_eraser": "橡皮擦",
        "tool_edit_text": "编辑文字",

        "color": "颜色",
        "more_colors": "更多...",
        "prev_page": "< 上一页",
        "next_page": "下一页 >",

        "status_ready": "请打开 PDF、HWP 或 Markdown 文件。(也可以将文件拖放到此处)",
        "status_opened": "已打开:{path}",
        "status_saved": "已保存:{path}",
        "status_tool": "工具:{tool}",
        "status_not_found": "未找到“{text}”。",
        "status_copied": "已复制。",
        "status_capture_place": "在页面上点击或拖动以放置并调整截图大小。(Esc:取消)",
        "status_capture_cancelled": "已取消截图。",
        "status_capture_placed": "已插入截图。",

        "dialog_open_pdf": "打开文档",
        "dialog_save_as": "另存为",
        "filter_open": "所有支持的文档 (*.pdf *.hwp *.hwpx *.md *.markdown);;PDF 文件 (*.pdf);;HWP 文档 (*.hwp *.hwpx);;Markdown (*.md *.markdown);;所有文件 (*.*)",
        "filter_pdf": "PDF 文件 (*.pdf)",
        "hwp_save_notice": "为了保护原文件，HWP 文档将保存为 PDF 文件。",
        "color_dialog_title": "选择颜色",

        "open_failed_title": "打开失败",
        "open_failed_msg": "无法打开文件:\n{exc}",
        "save_failed_title": "保存失败",
        "save_failed_msg": "保存时发生错误:\n{exc}",
        "print_failed_title": "打印失败",
        "print_failed_msg": "打印时发生错误:\n{exc}",

        "cancel": "取消",
        "printer_label": "打印机",
        "orientation_label": "打印方向",
        "orientation_portrait": "纵向",
        "orientation_landscape": "横向",
        "copies_label": "打印份数",
        "page_range_label": "页面",
        "page_range_all": "所有页面",
        "page_range_current": "当前页面",

        "delete_impossible_title": "无法删除",
        "delete_impossible_msg": "无法删除最后一页。",
        "delete_page_title": "删除页面",
        "delete_page_msg": "要删除第 {n} 页吗?",

        "exit_title": "退出",
        "exit_msg": "有未保存的更改。仍要退出吗?",

        "search_placeholder": "输入查找内容后按 Enter",
        "search_label": "查找:",
        "search_prev": "◀ 上一个",
        "search_next": "下一个 ▶",

        "thumb_dock_title": "页面",
        "page_indicator": "第 {current} / {total} 页",
        "untitled": "未命名",
        "close_tab": "关闭标签页",

        "note_title": "添加批注",
        "note_label": "请输入批注内容:",
        "freetext_title": "添加文本框",
        "freetext_label": "请输入要显示的文字:",
        "edit_text_title": "编辑文字",
        "edit_text_label": "编辑所选区域的文字(原文字将被删除):",

        "lang_changed": "语言已更改。重启程序后生效。",

        "about_designed_by": "设计者:{name}",
    },
    "ja": {
        "app_title": "PDF Super Viewer (HWP,MD)",
        "menu_file": "ファイル",
        "menu_edit": "編集",
        "menu_page": "ページ",
        "menu_view": "表示",
        "menu_language": "言語 Language",
        "menu_help": "ヘルプ",

        "open": "開く...",
        "save": "保存",
        "save_as": "名前を付けて保存...",
        "print": "印刷...",
        "print_preview_title": "印刷プレビュー",
        "exit": "終了",

        "undo": "元に戻す",
        "redo": "やり直し",
        "find": "検索...",
        "copy": "コピー",
        "capture": "キャプチャ...",

        "insert_page": "白紙ページを挿入",
        "delete_page": "現在のページを削除",
        "rotate_page": "現在のページを回転 (90°)",

        "zoom_in": "拡大",
        "zoom_out": "縮小",
        "zoom_reset": "実際のサイズ",
        "fit_width": "幅に合わせる",
        "fit_page": "ページに合わせる",
        "toggle_thumbnails": "ページ一覧の表示/非表示",

        "about": "バージョン情報...",

        "tool_none": "選択",
        "tool_highlight": "ハイライト",
        "tool_underline": "下線",
        "tool_strikeout": "取り消し線",
        "tool_note": "ノート",
        "tool_freetext": "テキストボックス",
        "tool_pen": "ペン",
        "tool_rect": "四角形",
        "tool_ellipse": "円",
        "tool_eraser": "消しゴム",
        "tool_edit_text": "テキスト編集",

        "color": "色",
        "more_colors": "もっと見る...",
        "prev_page": "< 前へ",
        "next_page": "次へ >",

        "status_ready": "PDF、HWP、またはMarkdownファイルを開いてください。(ドラッグ&ドロップも可能です)",
        "status_opened": "開きました: {path}",
        "status_saved": "保存しました: {path}",
        "status_tool": "ツール: {tool}",
        "status_not_found": "「{text}」が見つかりません。",
        "status_copied": "コピーしました。",
        "status_capture_place": "ページ上でクリックまたはドラッグしてキャプチャを配置・サイズ調整してください。(Esc: キャンセル)",
        "status_capture_cancelled": "キャプチャをキャンセルしました。",
        "status_capture_placed": "キャプチャを挿入しました。",

        "dialog_open_pdf": "ドキュメントを開く",
        "dialog_save_as": "名前を付けて保存",
        "filter_open": "サポートされているすべてのドキュメント (*.pdf *.hwp *.hwpx *.md *.markdown);;PDFファイル (*.pdf);;HWPドキュメント (*.hwp *.hwpx);;Markdown (*.md *.markdown);;すべてのファイル (*.*)",
        "filter_pdf": "PDFファイル (*.pdf)",
        "hwp_save_notice": "元のファイルを保護するため、HWPドキュメントはPDFファイルとして保存されます。",
        "color_dialog_title": "色の選択",

        "open_failed_title": "開けませんでした",
        "open_failed_msg": "ファイルを開けませんでした:\n{exc}",
        "save_failed_title": "保存に失敗しました",
        "save_failed_msg": "保存中にエラーが発生しました:\n{exc}",
        "print_failed_title": "印刷に失敗しました",
        "print_failed_msg": "印刷中にエラーが発生しました:\n{exc}",

        "cancel": "キャンセル",
        "printer_label": "プリンター",
        "orientation_label": "印刷方向",
        "orientation_portrait": "縦",
        "orientation_landscape": "横",
        "copies_label": "印刷部数",
        "page_range_label": "ページ",
        "page_range_all": "すべてのページ",
        "page_range_current": "現在のページ",

        "delete_impossible_title": "削除できません",
        "delete_impossible_msg": "最後の1ページは削除できません。",
        "delete_page_title": "ページを削除",
        "delete_page_msg": "{n}ページ目を削除しますか?",

        "exit_title": "終了",
        "exit_msg": "保存されていない変更があります。終了してもよろしいですか?",

        "search_placeholder": "検索内容を入力してEnterを押してください",
        "search_label": "検索:",
        "search_prev": "◀ 前へ",
        "search_next": "次へ ▶",

        "thumb_dock_title": "ページ",
        "page_indicator": "{current} / {total} ページ",
        "untitled": "無題",
        "close_tab": "タブを閉じる",

        "note_title": "ノートを追加",
        "note_label": "ノートの内容を入力してください:",
        "freetext_title": "テキストボックスを追加",
        "freetext_label": "表示するテキストを入力してください:",
        "edit_text_title": "テキストを編集",
        "edit_text_label": "選択した範囲のテキストを編集してください(元のテキストは削除されます):",

        "lang_changed": "言語が変更されました。プログラムを再起動すると適用されます。",

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
