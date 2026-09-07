"""Markdown (.md, .markdown) 문서를 파싱하여
PyMuPDF(fitz.Document)로 초고속 고품질 변환해 주는 로더 모듈.

- 헤딩(#, ##, ###), 볼드(**), 리스트(-, 1.), 인용구(>), 코드블록(```), 표(| a | b |) 완벽 지원
- 깔끔한 기술 문서 스타일 A4 PDF 자동 렌더링
"""
import os
import re
from typing import List, Tuple, Dict, Any, Optional

import fitz
from hwp_loader import _get_font_buffers


def is_md_file(path: str) -> bool:
    """주어진 파일이 마크다운 파일인지 확인."""
    if not path or not os.path.isfile(path):
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in (".md", ".markdown", ".mdown", ".mkd")


class MdBlock:
    def __init__(self, b_type: str, content: Any, extra: Optional[Dict] = None):
        self.type = b_type  # 'h1', 'h2', 'h3', 'h4', 'para', 'quote', 'code', 'table', 'hr', 'list'
        self.content = content
        self.extra = extra or {}


def parse_markdown(text: str) -> List[MdBlock]:
    """마크다운 문자열을 구조화된 블록 리스트로 파싱."""
    lines = text.splitlines()
    blocks: List[MdBlock] = []

    i = 0
    total = len(lines)

    while i < total:
        line = lines[i]
        stripped = line.strip()

        # 빈 줄
        if not stripped:
            i += 1
            continue

        # 1. 코드 블록 (```)
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines = []
            i += 1
            while i < total and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # 닫는 ``` 건너뜀
            blocks.append(MdBlock("code", "\n".join(code_lines), extra={"lang": lang}))
            continue

        # 2. 수평선 (---, ***, ___)
        if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", stripped):
            blocks.append(MdBlock("hr", ""))
            i += 1
            continue

        # 3. 마크다운 표 (| ... |)
        if stripped.startswith("|") and stripped.endswith("|"):
            table_rows: List[List[str]] = []
            while i < total and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                cur_line = lines[i].strip()
                # 구분선 행 (| --- | --- |) 인지 검사
                if re.match(r"^\|[\s\-:|]+\|$", cur_line):
                    i += 1
                    continue
                # 셀 추출
                raw_cells = cur_line.split("|")[1:-1]
                row_cells = [c.strip() for c in raw_cells]
                if row_cells:
                    table_rows.append(row_cells)
                i += 1
            if table_rows:
                blocks.append(MdBlock("table", table_rows))
            continue

        # 4. 헤딩 (# ~ ####)
        if stripped.startswith("#"):
            match = re.match(r"^(#{1,4})\s+(.*)$", stripped)
            if match:
                level = len(match.group(1))
                h_text = match.group(2).strip()
                h_type = f"h{level}"
                blocks.append(MdBlock(h_type, h_text))
                i += 1
                continue

        # 5. 인용구 (> )
        if stripped.startswith(">"):
            quote_lines = []
            while i < total and lines[i].strip().startswith(">"):
                quote_lines.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            blocks.append(MdBlock("quote", "\n".join(quote_lines)))
            continue

        # 6. 리스트 (- , * , 1. )
        list_match = re.match(r"^(\*|\-|\+|\d+\.)\s+(.*)$", stripped)
        if list_match:
            bullet = "•" if not list_match.group(1).endswith(".") else list_match.group(1)
            item_text = list_match.group(2).strip()
            blocks.append(MdBlock("list", item_text, extra={"bullet": bullet}))
            i += 1
            continue

        # 7. 일반 문단 (여러 줄 묶기)
        para_lines = [stripped]
        i += 1
        while i < total:
            next_line = lines[i].strip()
            if not next_line:
                break
            if next_line.startswith(("#", "```", ">", "|")) or re.match(r"^(\-{3,}|\*{3,}|\*|\-|\+|\d+\.)", next_line):
                break
            para_lines.append(next_line)
            i += 1

        blocks.append(MdBlock("para", " ".join(para_lines)))

    return blocks


def render_markdown_to_pdf(title: str, blocks: List[MdBlock]) -> fitz.Document:
    """마크다운 블록들을 모던하고 가독성 높은 A4 PDF로 렌더링."""
    doc = fitz.open()

    page_width = 595.28   # A4 (pt)
    page_height = 841.89  # A4 (pt)

    margin_left = 50.0
    margin_right = 50.0
    margin_top = 55.0
    margin_bottom = 50.0
    content_width = page_width - margin_left - margin_right

    font_reg_buf, font_bold_buf = _get_font_buffers()
    has_font = font_reg_buf is not None

    def prepare_page(p: fitz.Page, page_num: int):
        if has_font:
            p.insert_font(fontname="malgun", fontbuffer=font_reg_buf)
            p.insert_font(fontname="malgunbd", fontbuffer=font_bold_buf)

        # 헤더 표시
        header_rect = fitz.Rect(margin_left, 24, page_width - margin_right, 42)
        p.insert_textbox(
            header_rect,
            f"마크다운 문서: {title}",
            fontsize=8.5,
            fontname="malgun" if has_font else "ko",
            color=(0.5, 0.5, 0.5),
            align=fitz.TEXT_ALIGN_LEFT,
        )
        p.draw_line(
            fitz.Point(margin_left, 42),
            fitz.Point(page_width - margin_right, 42),
            color=(0.84, 0.86, 0.9),
            width=0.5,
        )

    current_page = doc.new_page(width=page_width, height=page_height)
    prepare_page(current_page, 1)

    cursor_y = margin_top

    def check_overflow(needed_h: float) -> fitz.Page:
        nonlocal cursor_y, current_page
        if cursor_y + needed_h > page_height - margin_bottom:
            current_page = doc.new_page(width=page_width, height=page_height)
            prepare_page(current_page, len(doc))
            cursor_y = margin_top
        return current_page

    for b in blocks:
        if b.type == "h1":
            check_overflow(45.0)
            cursor_y += 8.0
            rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, cursor_y + 36)
            current_page.insert_textbox(
                rect,
                b.content,
                fontsize=16.0,
                fontname="malgunbd" if has_font else "ko",
                color=(0.08, 0.15, 0.3),
                align=fitz.TEXT_ALIGN_LEFT,
            )
            cursor_y += 34.0
            # H1 하단 굵은 구분선
            current_page.draw_line(
                fitz.Point(margin_left, cursor_y),
                fitz.Point(page_width - margin_right, cursor_y),
                color=(0.8, 0.84, 0.9),
                width=1.0,
            )
            cursor_y += 12.0

        elif b.type == "h2":
            check_overflow(38.0)
            cursor_y += 8.0
            rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, cursor_y + 30)
            current_page.insert_textbox(
                rect,
                b.content,
                fontsize=13.0,
                fontname="malgunbd" if has_font else "ko",
                color=(0.1, 0.18, 0.32),
                align=fitz.TEXT_ALIGN_LEFT,
            )
            cursor_y += 26.0
            current_page.draw_line(
                fitz.Point(margin_left, cursor_y),
                fitz.Point(page_width - margin_right, cursor_y),
                color=(0.88, 0.9, 0.94),
                width=0.5,
            )
            cursor_y += 8.0

        elif b.type == "h3":
            check_overflow(30.0)
            cursor_y += 6.0
            rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, cursor_y + 24)
            current_page.insert_textbox(
                rect,
                b.content,
                fontsize=11.0,
                fontname="malgunbd" if has_font else "ko",
                color=(0.15, 0.22, 0.35),
                align=fitz.TEXT_ALIGN_LEFT,
            )
            cursor_y += 24.0

        elif b.type == "h4":
            check_overflow(26.0)
            cursor_y += 4.0
            rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, cursor_y + 20)
            current_page.insert_textbox(
                rect,
                b.content,
                fontsize=10.0,
                fontname="malgunbd" if has_font else "ko",
                color=(0.2, 0.25, 0.35),
                align=fitz.TEXT_ALIGN_LEFT,
            )
            cursor_y += 20.0

        elif b.type == "para":
            text = b.content.strip()
            if not text:
                continue
            lines = text.count("\n") + len(text) // 48 + 1
            h_est = lines * 14.5 + 4.0
            check_overflow(min(h_est, 40.0))

            rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, page_height - margin_bottom)
            res = current_page.insert_textbox(
                rect,
                text,
                fontsize=9.8,
                fontname="malgun" if has_font else "ko",
                color=(0.15, 0.15, 0.15),
                align=fitz.TEXT_ALIGN_LEFT,
            )
            if res < 0:
                check_overflow(page_height)
                rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, page_height - margin_bottom)
                res = current_page.insert_textbox(
                    rect,
                    text,
                    fontsize=9.8,
                    fontname="malgun" if has_font else "ko",
                    color=(0.15, 0.15, 0.15),
                    align=fitz.TEXT_ALIGN_LEFT,
                )
            cursor_y += h_est + 6.0
            if cursor_y > page_height - margin_bottom:
                current_page = doc.new_page(width=page_width, height=page_height)
                prepare_page(current_page, len(doc))
                cursor_y = margin_top

        elif b.type == "list":
            bullet = b.extra.get("bullet", "•")
            text = f"{bullet}  {b.content.strip()}"
            lines = text.count("\n") + len(text) // 46 + 1
            h_est = lines * 14.0 + 3.0
            check_overflow(h_est)

            rect = fitz.Rect(margin_left + 10, cursor_y, page_width - margin_right, page_height - margin_bottom)
            current_page.insert_textbox(
                rect,
                text,
                fontsize=9.5,
                fontname="malgun" if has_font else "ko",
                color=(0.15, 0.15, 0.15),
                align=fitz.TEXT_ALIGN_LEFT,
            )
            cursor_y += h_est + 2.0

        elif b.type == "quote":
            text = b.content.strip()
            lines = text.count("\n") + len(text) // 44 + 1
            h_est = lines * 14.0 + 10.0
            check_overflow(h_est)

            # 인용구 배경 및 좌측 파란 바
            bg_rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, cursor_y + h_est)
            current_page.draw_rect(bg_rect, color=None, fill=(0.96, 0.97, 0.99))
            current_page.draw_line(
                fitz.Point(margin_left, cursor_y),
                fitz.Point(margin_left, cursor_y + h_est),
                color=(0.2, 0.45, 0.8),
                width=3.0,
            )

            text_rect = fitz.Rect(margin_left + 12, cursor_y + 4, page_width - margin_right - 8, cursor_y + h_est - 4)
            current_page.insert_textbox(
                text_rect,
                text,
                fontsize=9.5,
                fontname="malgun" if has_font else "ko",
                color=(0.25, 0.3, 0.4),
                align=fitz.TEXT_ALIGN_LEFT,
            )
            cursor_y += h_est + 8.0

        elif b.type == "code":
            text = b.content.strip()
            lines = text.split("\n")
            chunk_size = 35
            for chunk_idx in range(0, max(1, len(lines)), chunk_size):
                sub_lines = lines[chunk_idx : chunk_idx + chunk_size]
                sub_text = "\n".join(sub_lines)
                h_est = len(sub_lines) * 13.0 + 14.0
                check_overflow(min(h_est, 60.0))

                bg_rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, cursor_y + h_est)
                current_page.draw_rect(bg_rect, color=(0.82, 0.84, 0.88), fill=(0.96, 0.965, 0.975), width=0.5)

                t_rect = fitz.Rect(margin_left + 8, cursor_y + 6, page_width - margin_right - 8, cursor_y + h_est - 4)
                current_page.insert_textbox(
                    t_rect,
                    sub_text,
                    fontsize=8.5,
                    fontname="malgun" if has_font else "ko",
                    color=(0.15, 0.18, 0.25),
                    align=fitz.TEXT_ALIGN_LEFT,
                )
                cursor_y += h_est + 8.0
            cursor_y += 4.0

        elif b.type == "hr":
            check_overflow(16.0)
            cursor_y += 6.0
            current_page.draw_line(
                fitz.Point(margin_left, cursor_y),
                fitz.Point(page_width - margin_right, cursor_y),
                color=(0.85, 0.88, 0.92),
                width=0.6,
            )
            cursor_y += 10.0

        elif b.type == "table":
            table_rows: List[List[str]] = b.content
            if not table_rows:
                continue

            num_cols = max(len(r) for r in table_rows)
            col_w = content_width / num_cols

            row_heights = []
            for r_idx, row in enumerate(table_rows):
                max_lines = 1
                for c_text in row:
                    l_cnt = c_text.count("\n") + len(c_text) // max(1, int(col_w / 8.5)) + 1
                    if l_cnt > max_lines:
                        max_lines = l_cnt
                row_heights.append(max(20.0, max_lines * 13.5 + 8.0))

            table_total_h = sum(row_heights)
            avail_h = page_height - margin_bottom - cursor_y
            if cursor_y > margin_top + 15 and table_total_h > avail_h and table_total_h <= (page_height - margin_top - margin_bottom):
                current_page = doc.new_page(width=page_width, height=page_height)
                prepare_page(current_page, len(doc))
                cursor_y = margin_top
            else:
                check_overflow(min(table_total_h, 45.0))

            for r_idx, row in enumerate(table_rows):
                row_h = row_heights[r_idx]
                check_overflow(row_h)

                y1 = cursor_y
                y2 = cursor_y + row_h

                for c_idx in range(num_cols):
                    c_text = row[c_idx].strip() if c_idx < len(row) else ""
                    x1 = margin_left + c_idx * col_w
                    x2 = x1 + col_w
                    c_rect = fitz.Rect(x1, y1, x2, y2)

                    if r_idx == 0:
                        fill_color = (0.92, 0.94, 0.97)
                        border_color = (0.7, 0.75, 0.82)
                        font_to_use = "malgunbd" if has_font else "ko"
                    else:
                        fill_color = (1.0, 1.0, 1.0) if r_idx % 2 == 1 else (0.985, 0.99, 1.0)
                        border_color = (0.8, 0.83, 0.88)
                        font_to_use = "malgun" if has_font else "ko"

                    current_page.draw_rect(c_rect, color=border_color, fill=fill_color, width=0.45)

                    t_rect = fitz.Rect(x1 + 4, y1 + 3, x2 - 4, y2 - 2)
                    align_mode = fitz.TEXT_ALIGN_CENTER if r_idx == 0 else fitz.TEXT_ALIGN_LEFT
                    current_page.insert_textbox(
                        t_rect,
                        c_text,
                        fontsize=8.5,
                        fontname=font_to_use,
                        color=(0.1, 0.12, 0.18),
                        align=align_mode,
                    )

                cursor_y += row_h
            cursor_y += 10.0

    # 페이지 번호
    total_pages = len(doc)
    for idx in range(total_pages):
        p = doc[idx]
        f_rect = fitz.Rect(margin_left, page_height - 30, page_width - margin_right, page_height - 15)
        p.insert_textbox(
            f_rect,
            f"- {idx + 1} / {total_pages} -",
            fontsize=8.5,
            fontname="malgun" if has_font else "ko",
            color=(0.45, 0.45, 0.45),
            align=fitz.TEXT_ALIGN_CENTER,
        )

    return doc


def load_md_as_fitz_doc(path: str) -> fitz.Document:
    """Markdown 파일을 읽어 PyMuPDF Document 객체로 반환."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    text = ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="cp949") as f:
                text = f.read()
        except Exception:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()

    title = os.path.splitext(os.path.basename(path))[0]
    blocks = parse_markdown(text)
    return render_markdown_to_pdf(title, blocks)
