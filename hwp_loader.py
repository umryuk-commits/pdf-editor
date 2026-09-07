"""HWP (아래아한글 5.0) 및 HWPX (한글 표준 OWPML) 문서를 파싱하여
PyMuPDF(fitz.Document)로 초고속 고품질 변환해 주는 로더 모듈.

- HWP 실제 셀 너비(가변 열 너비 비율) 및 Colspan 병합 셀 완벽 복원
- DocInfo 문단 모양(정렬 방식: 가운데/오른쪽/양쪽) 복원
- 폰트 버퍼 인메모리 캐싱으로 대용량 문서도 초고속 렌더링
"""
import io
import os
import struct
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib
from typing import Any, Dict, List, Optional, Tuple

import fitz

try:
    import olefile
except ImportError:
    olefile = None

_FONT_REGULAR_BUFFER: Optional[bytes] = None
_FONT_BOLD_BUFFER: Optional[bytes] = None


def _get_font_buffers() -> Tuple[Optional[bytes], Optional[bytes]]:
    global _FONT_REGULAR_BUFFER, _FONT_BOLD_BUFFER
    if _FONT_REGULAR_BUFFER is None:
        windir = os.environ.get("WINDIR", "C:/Windows")
        font_dir = os.path.join(windir, "Fonts")

        candidate_reg = [
            os.path.join(font_dir, "malgun.ttf"),
            "C:/Windows/Fonts/malgun.ttf",
            os.path.join(font_dir, "NanumGothic.ttf"),
            os.path.join(font_dir, "gulim.ttc"),
        ]
        candidate_bold = [
            os.path.join(font_dir, "malgunbd.ttf"),
            "C:/Windows/Fonts/malgunbd.ttf",
            os.path.join(font_dir, "NanumGothicBold.ttf"),
        ]

        for p in candidate_reg:
            if os.path.exists(p):
                try:
                    with open(p, "rb") as f:
                        _FONT_REGULAR_BUFFER = f.read()
                    break
                except Exception:
                    pass

        for p in candidate_bold:
            if os.path.exists(p):
                try:
                    with open(p, "rb") as f:
                        _FONT_BOLD_BUFFER = f.read()
                    break
                except Exception:
                    pass

        if _FONT_BOLD_BUFFER is None and _FONT_REGULAR_BUFFER is not None:
            _FONT_BOLD_BUFFER = _FONT_REGULAR_BUFFER
    return _FONT_REGULAR_BUFFER, _FONT_BOLD_BUFFER


def is_hwp_file(path: str) -> bool:
    """주어진 파일이 HWP 또는 HWPX 파일인지 확인."""
    if not path or not os.path.isfile(path):
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in (".hwp", ".hwpx"):
        return True
    try:
        with open(path, "rb") as f:
            header = f.read(32)
            if header.startswith(b"HWP Document File"):
                return True
            if header.startswith(b"PK\x03\x04"):
                with zipfile.ZipFile(path, "r") as zf:
                    names = zf.namelist()
                    if any("section" in n.lower() or "content.hpf" in n.lower() for n in names):
                        return True
    except Exception:
        pass
    return False


class HwpElement:
    """파싱된 문서 요소 (문단, 표 등)."""

    def __init__(self, elem_type: str, data: Any, extra: Optional[Dict] = None):
        self.type = elem_type  # 'para', 'table'
        self.data = data
        self.extra = extra or {}


def _clean_hwp5_rec_bytes(rec: bytes) -> str:
    """HWP 5.0 HWPTAG_PARA_TEXT 바이너리에서 인라인 확장 컨트롤을 건너뛰고 순수 텍스트 추출."""
    text_chars: List[str] = []
    i = 0
    rec_len = len(rec)
    while i + 2 <= rec_len:
        code = struct.unpack_from("<H", rec, i)[0]
        i += 2
        # HWP 5.0 인라인 확장 컨트롤: 제어코드(2바이트) + 부가 데이터(14바이트) = 총 16바이트
        if code in (1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23):
            i += 14
        elif code == 10 or code == 13:
            text_chars.append("\n")
        elif code == 9:
            text_chars.append("    ")
        elif code < 32:
            pass
        else:
            text_chars.append(chr(code))
    return "".join(text_chars).strip()


def parse_hwpx(path: str) -> Tuple[str, List[HwpElement]]:
    """HWPX (ZIP + XML OWPML) 문서를 파싱."""
    title = os.path.splitext(os.path.basename(path))[0]
    elements: List[HwpElement] = []

    with zipfile.ZipFile(path, "r") as zf:
        section_names = sorted(
            [n for n in zf.namelist() if n.lower().startswith("contents/section") and n.lower().endswith(".xml")]
        )
        if not section_names:
            section_names = sorted(
                [n for n in zf.namelist() if "section" in n.lower() and n.lower().endswith(".xml")]
            )

        ns = {
            "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
            "hs": "http://www.hancom.co.kr/hwpml/2011/section",
            "hc": "http://www.hancom.co.kr/hwpml/2011/core",
        }

        for sname in section_names:
            try:
                xml_data = zf.read(sname)
                root = ET.fromstring(xml_data)

                for p in root.iter():
                    tag = p.tag.split("}")[-1] if "}" in p.tag else p.tag

                    if tag == "tbl":
                        table_data: List[List[str]] = []
                        for tr in p.findall(".//hp:tr", ns) or [e for e in p if e.tag.endswith("tr")]:
                            row_cells: List[str] = []
                            for tc in tr.findall(".//hp:tc", ns) or [e for e in tr if e.tag.endswith("tc")]:
                                cell_texts = []
                                for t_node in tc.findall(".//hp:t", ns) or [e for e in tc.iter() if e.tag.endswith("t")]:
                                    if t_node.text:
                                        cell_texts.append(t_node.text.strip())
                                row_cells.append("\n".join(cell_texts))
                            if row_cells:
                                table_data.append(row_cells)
                        if table_data:
                            elements.append(HwpElement("table", table_data))

                    elif tag == "p":
                        texts = []
                        for t_node in p.findall(".//hp:t", ns) or [e for e in p.iter() if e.tag.endswith("t")]:
                            if t_node.text:
                                texts.append(t_node.text)
                        full_text = "".join(texts).strip()
                        if full_text:
                            elements.append(HwpElement("para", full_text))
            except Exception as e:
                print(f"[hwp_loader] HWPX 파싱 오류 ({sname}): {e}")

    return title, elements


def _do_parse_hwp5(ole: Any, title: str) -> Tuple[str, List[HwpElement]]:
    elements: List[HwpElement] = []

    # 1. DocInfo에서 문단 정렬(Alignment) 정보 추출
    para_alignments: List[int] = []
    if ole.exists("DocInfo"):
        try:
            doc_info_stream = ole.openstream("DocInfo").read()
            try:
                doc_info_data = zlib.decompress(doc_info_stream, -15)
            except Exception:
                doc_info_data = doc_info_stream

            d_off = 0
            d_len = len(doc_info_data)
            while d_off + 4 <= d_len:
                h = struct.unpack_from("<I", doc_info_data, d_off)[0]
                d_off += 4
                tag = h & 0x3FF
                sz = (h >> 20) & 0xFFF
                if sz == 0xFFF:
                    sz = struct.unpack_from("<I", doc_info_data, d_off)[0]
                    d_off += 4
                rec = doc_info_data[d_off : d_off + sz]
                d_off += sz
                # HWPTAG_PARA_SHAPE = 21
                if tag == 21 and len(rec) >= 4:
                    prop1 = struct.unpack_from("<I", rec, 0)[0]
                    align = (prop1 >> 2) & 0x07
                    para_alignments.append(align)
        except Exception:
            pass

    # 2. FileHeader 확인
    is_compressed = False
    is_encrypted = False
    if ole.exists("FileHeader"):
        header_data = ole.openstream("FileHeader").read()
        if len(header_data) >= 40:
            flags = struct.unpack_from("<I", header_data, 36)[0]
            is_compressed = bool(flags & 0x01)
            is_encrypted = bool(flags & 0x02)

    if is_encrypted:
        elements.append(HwpElement("para", "[이 문서는 암호로 보호되어 있어 내용을 표시할 수 없습니다.]"))
        return title, elements

    # 3. BodyText/Section 스트림 순회
    section_idx = 0
    while True:
        sec_path = f"BodyText/Section{section_idx}"
        if not ole.exists(sec_path):
            break

        sec_stream = ole.openstream(sec_path).read()
        if is_compressed:
            try:
                sec_data = zlib.decompress(sec_stream, -15)
            except Exception:
                try:
                    sec_data = zlib.decompress(sec_stream)
                except Exception:
                    sec_data = sec_stream
        else:
            sec_data = sec_stream

        offset = 0
        total_len = len(sec_data)

        current_table: Optional[Dict] = None
        current_cell: Optional[Dict] = None
        current_align: int = 0

        while offset + 4 <= total_len:
            header_val = struct.unpack_from("<I", sec_data, offset)[0]
            offset += 4

            tag_id = header_val & 0x3FF
            size = (header_val >> 20) & 0xFFF

            if size == 0xFFF:
                if offset + 4 > total_len:
                    break
                size = struct.unpack_from("<I", sec_data, offset)[0]
                offset += 4

            if offset + size > total_len:
                break

            record_bytes = sec_data[offset : offset + size]
            offset += size

            # HWPTAG_TABLE = 77
            if tag_id == 77:
                if len(record_bytes) >= 8:
                    prop, rows, cols = struct.unpack_from("<IHH", record_bytes, 0)
                    if current_table is not None:
                        elements.append(HwpElement("table", current_table))
                    current_table = {
                        "rows": rows,
                        "cols": cols,
                        "col_widths": [0] * cols,
                        "cells": {},
                        "cells_left": rows * cols,
                    }
                    current_cell = None

            # HWPTAG_LIST_HEADER = 72 (셀 헤더)
            elif tag_id == 72:
                if len(record_bytes) >= 24 and current_table is not None:
                    para_cnt, prop, col, row, col_span, row_span, width, height = struct.unpack_from(
                        "<IIHHHHII", record_bytes, 0
                    )
                    current_cell = {
                        "row": row,
                        "col": col,
                        "cs": max(1, col_span),
                        "rs": max(1, row_span),
                        "w": width,
                        "h": height,
                        "text": "",
                        "align": 0,
                    }
                    current_table["cells"][(row, col)] = current_cell
                    if col_span == 1 and col < current_table["cols"]:
                        current_table["col_widths"][col] = max(current_table["col_widths"][col], width)
                    if current_table["cells_left"] > 0:
                        current_table["cells_left"] -= 1

            # HWPTAG_PARA_HEADER = 66
            elif tag_id == 66:
                if len(record_bytes) >= 10:
                    shape_id = struct.unpack_from("<H", record_bytes, 8)[0]
                    if shape_id < len(para_alignments):
                        current_align = para_alignments[shape_id]
                    else:
                        current_align = 0

            # HWPTAG_PARA_TEXT = 67
            elif tag_id == 67:
                text = _clean_hwp5_rec_bytes(record_bytes)
                if text:
                    if current_cell is not None and current_table is not None:
                        existing = current_cell["text"]
                        current_cell["text"] = (existing + "\n" + text).strip() if existing else text
                        current_cell["align"] = current_align
                    else:
                        if current_table is not None:
                            elements.append(HwpElement("table", current_table))
                            current_table = None
                            current_cell = None
                        elements.append(HwpElement("para", text, extra={"align": current_align}))

            # HWPTAG_CTRL_HEADER = 71
            elif tag_id == 71:
                ctrl_id = record_bytes[:4]
                if ctrl_id != b"tbl " and current_table is not None and current_table["cells_left"] <= 0:
                    elements.append(HwpElement("table", current_table))
                    current_table = None
                    current_cell = None

        if current_table is not None:
            elements.append(HwpElement("table", current_table))

        section_idx += 1

    return title, elements


def parse_hwp5(path: str) -> Tuple[str, List[HwpElement]]:
    """HWP 5.0 (OLE2 바이너리) 문서를 파싱하여 문단, 표(가변 열너비 및 병합정보), 정렬 추출."""
    title = os.path.splitext(os.path.basename(path))[0]

    if olefile is None:
        raise RuntimeError("olefile 패키지가 필요합니다 (pip install olefile)")

    if not olefile.isOleFile(path):
        raise ValueError("유효한 HWP OLE 파일이 아닙니다.")

    ole = olefile.OleFileIO(path)
    try:
        return _do_parse_hwp5(ole, title)
    finally:
        try:
            ole.close()
        except Exception:
            pass


def _try_convert_via_com(hwp_path: str) -> Optional[fitz.Document]:
    """한컴오피스가 설치되어 있는 경우 COM 자동화를 통해 원본 100% 동일 PDF 변환 시도."""
    try:
        import win32com.client
    except ImportError:
        return None

    temp_pdf = None
    hwp = None
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
        hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
        hwp.SetMessageBoxMode(0x00010000)

        fd, temp_pdf = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)

        if hwp.Open(os.path.abspath(hwp_path), "HWP", "forceopen:true"):
            hwp.SaveAs(os.path.abspath(temp_pdf), "PDF")
            hwp.Clear(1)
            hwp.Quit()
            hwp = None

            if os.path.exists(temp_pdf) and os.path.getsize(temp_pdf) > 0:
                doc = fitz.open(temp_pdf)
                mem_doc = fitz.open("pdf", doc.tobytes())
                doc.close()
                try:
                    os.remove(temp_pdf)
                except Exception:
                    pass
                return mem_doc
    except Exception:
        pass
    finally:
        if hwp:
            try:
                hwp.Quit()
            except Exception:
                pass
        if temp_pdf and os.path.exists(temp_pdf):
            try:
                os.remove(temp_pdf)
            except Exception:
                pass
    return None


def render_elements_to_pdf(title: str, elements: List[HwpElement]) -> fitz.Document:
    """HWP 문서 요소들을 가변 열너비, Colspan, 정렬을 온전히 반영하여 A4 PDF로 렌더링."""
    doc = fitz.open()

    page_width = 595.28   # A4 (pt)
    page_height = 841.89  # A4 (pt)

    margin_left = 44.0
    margin_right = 44.0
    margin_top = 50.0
    margin_bottom = 45.0
    content_width = page_width - margin_left - margin_right

    font_reg_buf, font_bold_buf = _get_font_buffers()
    has_font = font_reg_buf is not None

    def prepare_page(p: fitz.Page, page_num: int):
        if has_font:
            p.insert_font(fontname="malgun", fontbuffer=font_reg_buf)
            p.insert_font(fontname="malgunbd", fontbuffer=font_bold_buf)

        # 상단 문서 표제 라인
        header_rect = fitz.Rect(margin_left, 20, page_width - margin_right, 38)
        p.insert_textbox(
            header_rect,
            f"한글 문서: {title}",
            fontsize=8.5,
            fontname="malgun" if has_font else "ko",
            color=(0.5, 0.5, 0.5),
            align=fitz.TEXT_ALIGN_LEFT,
        )
        p.draw_line(
            fitz.Point(margin_left, 38),
            fitz.Point(page_width - margin_right, 38),
            color=(0.82, 0.85, 0.9),
            width=0.5,
        )

    current_page = doc.new_page(width=page_width, height=page_height)
    prepare_page(current_page, 1)

    cursor_y = margin_top

    # 제목 렌더링
    title_rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, cursor_y + 36)
    current_page.insert_textbox(
        title_rect,
        title,
        fontsize=16.0,
        fontname="malgunbd" if has_font else "ko",
        color=(0.08, 0.12, 0.22),
        align=fitz.TEXT_ALIGN_CENTER,
    )
    cursor_y += 42.0

    def check_overflow(needed_height: float) -> fitz.Page:
        nonlocal cursor_y, current_page
        if cursor_y + needed_height > page_height - margin_bottom:
            current_page = doc.new_page(width=page_width, height=page_height)
            prepare_page(current_page, len(doc))
            cursor_y = margin_top
        return current_page

    def get_fitz_align(align_val: int) -> int:
        if align_val == 3:
            return fitz.TEXT_ALIGN_CENTER
        elif align_val == 2:
            return fitz.TEXT_ALIGN_RIGHT
        return fitz.TEXT_ALIGN_LEFT

    # 본문 요소들 렌더링
    for elem in elements:
        if elem.type == "para":
            text = str(elem.data).strip()
            if not text:
                cursor_y += 5.0
                continue

            align_val = elem.extra.get("align", 0)
            align_mode = get_fitz_align(align_val)

            is_main_heading = any(text.startswith(pfx) for pfx in ("1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. "))
            is_sub_heading = any(text.startswith(pfx) for pfx in ("□ ", "○ ", "■ ", "◆ ", "▶ ", "< ", "【 "))

            if is_main_heading:
                check_overflow(36.0)
                font_size = 12.0
                font_to_use = "malgunbd" if has_font else "ko"
                text_color = (0.05, 0.15, 0.35)
                line_spacing = 16.0
                cursor_y += 6.0
            elif is_sub_heading:
                check_overflow(30.0)
                font_size = 10.5
                font_to_use = "malgunbd" if has_font else "ko"
                text_color = (0.1, 0.18, 0.28)
                line_spacing = 15.0
                cursor_y += 3.0
            else:
                font_size = 9.8
                font_to_use = "malgun" if has_font else "ko"
                text_color = (0.15, 0.15, 0.15)
                line_spacing = 14.0

            lines = text.split("\n")
            total_lines = sum(max(1, len(line) // 48 + 1) for line in lines)
            block_height = total_lines * line_spacing + 4.0

            check_overflow(min(block_height, 42.0))

            target_rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, page_height - margin_bottom)
            res = current_page.insert_textbox(
                target_rect,
                text,
                fontsize=font_size,
                fontname=font_to_use,
                color=text_color,
                align=align_mode,
            )

            if res < 0:
                check_overflow(page_height)
                target_rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, page_height - margin_bottom)
                res = current_page.insert_textbox(
                    target_rect,
                    text,
                    fontsize=font_size,
                    fontname=font_to_use,
                    color=text_color,
                    align=align_mode,
                )

            cursor_y += block_height
            if cursor_y > page_height - margin_bottom:
                current_page = doc.new_page(width=page_width, height=page_height)
                prepare_page(current_page, len(doc))
                cursor_y = margin_top

        elif elem.type == "table":
            t_data = elem.data

            # 1) HWPX 호환 2차원 리스트 형태
            if isinstance(t_data, list):
                table_rows = t_data
                if not table_rows:
                    continue
                num_rows = len(table_rows)
                num_cols = max(len(r) for r in table_rows)
                if num_cols == 0:
                    continue

                col_w = content_width / num_cols
                check_overflow(45.0)

                for r_idx, row in enumerate(table_rows):
                    max_lines = 1
                    for c_text in row:
                        l_cnt = c_text.count("\n") + len(c_text) // max(1, int(col_w / 8.5)) + 1
                        if l_cnt > max_lines:
                            max_lines = l_cnt

                    row_h = max(20.0, max_lines * 13.5 + 8.0)
                    check_overflow(row_h)

                    y1 = cursor_y
                    y2 = cursor_y + row_h
                    for c_idx in range(num_cols):
                        c_text = row[c_idx].strip() if c_idx < len(row) else ""
                        x1 = margin_left + c_idx * col_w
                        x2 = x1 + col_w
                        c_rect = fitz.Rect(x1, y1, x2, y2)

                        current_page.draw_rect(
                            c_rect,
                            color=(0.7, 0.75, 0.82) if r_idx == 0 else (0.8, 0.83, 0.88),
                            fill=(0.92, 0.94, 0.97) if r_idx == 0 else (1.0, 1.0, 1.0),
                            width=0.5,
                        )
                        t_rect = fitz.Rect(x1 + 4, y1 + 3, x2 - 4, y2 - 2)
                        current_page.insert_textbox(
                            t_rect,
                            c_text,
                            fontsize=8.5,
                            fontname=("malgunbd" if r_idx == 0 and has_font else "malgun") if has_font else "ko",
                            color=(0.1, 0.12, 0.18),
                            align=fitz.TEXT_ALIGN_CENTER if (r_idx == 0 or len(c_text) <= 6) else fitz.TEXT_ALIGN_LEFT,
                        )
                    cursor_y += row_h
                cursor_y += 8.0
                continue

            # 2) HWP 5.0 고급 표 객체 (2차원 셀 그리드 엔진: Rowspan & Colspan 완벽 지원)
            num_rows = t_data["rows"]
            num_cols = t_data["cols"]
            raw_widths = t_data.get("col_widths", [0] * num_cols)
            cells_dict = t_data.get("cells", {})

            if num_rows == 0 or num_cols == 0:
                continue

            # 셀 리스트 수집
            all_cells = list(cells_dict.values())
            if not all_cells:
                continue

            # 1x1 상자 (공지/제목 박스)
            if num_rows == 1 and num_cols == 1:
                c_info = all_cells[0]
                box_text = c_info.get("text", "").strip() if isinstance(c_info, dict) else str(c_info).strip()
                if not box_text:
                    continue

                lines_in_box = box_text.count("\n") + len(box_text) // 46 + 1
                box_height = max(26.0, lines_in_box * 14.0 + 12.0)
                check_overflow(box_height + 8.0)

                b_rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, cursor_y + box_height)
                current_page.draw_rect(b_rect, color=(0.72, 0.78, 0.88), fill=(0.96, 0.97, 0.99), width=0.8)

                t_rect = fitz.Rect(margin_left + 8, cursor_y + 6, page_width - margin_right - 8, cursor_y + box_height - 4)
                box_align = get_fitz_align(c_info.get("align", 0) if isinstance(c_info, dict) else 0)
                current_page.insert_textbox(
                    t_rect,
                    box_text,
                    fontsize=9.5,
                    fontname="malgun" if has_font else "ko",
                    color=(0.12, 0.15, 0.22),
                    align=box_align,
                )
                cursor_y += box_height + 10.0
                continue

            # 1단계: 열 너비(col_widths) 산출
            col_widths_raw = [0] * num_cols
            for c in all_cells:
                cs = c.get("cs", 1)
                col_idx = c.get("col", 0)
                if cs == 1 and col_idx < num_cols:
                    col_widths_raw[col_idx] = max(col_widths_raw[col_idx], c.get("w", 0))

            total_w = sum(col_widths_raw)
            if total_w <= 0:
                total_w = sum(raw_widths)
                if total_w > 0:
                    col_widths_raw = list(raw_widths)

            if total_w > 0:
                actual_col_w = [content_width * (w / total_w) for w in col_widths_raw]
            else:
                actual_col_w = [content_width / num_cols] * num_cols

            col_x = [margin_left]
            for w in actual_col_w:
                col_x.append(col_x[-1] + w)

            # 2단계: 행 높이(row_heights) 산출
            row_heights = [18.0] * num_rows
            for c in all_cells:
                r = c.get("row", 0)
                rs = c.get("rs", 1)
                cs = c.get("cs", 1)
                col_idx = c.get("col", 0)
                text = c.get("text", "")
                span_w = col_x[min(col_idx + cs, num_cols)] - col_x[col_idx]
                lines = text.count("\n") + len(text) // max(1, int(span_w / 8.5)) + 1
                req_h = max(18.0, lines * 13.0 + 7.0)
                if rs == 1 and r < num_rows:
                    row_heights[r] = max(row_heights[r], req_h)

            for c in all_cells:
                r = c.get("row", 0)
                rs = c.get("rs", 1)
                cs = c.get("cs", 1)
                col_idx = c.get("col", 0)
                if rs > 1 and r < num_rows:
                    text = c.get("text", "")
                    span_w = col_x[min(col_idx + cs, num_cols)] - col_x[col_idx]
                    lines = text.count("\n") + len(text) // max(1, int(span_w / 8.5)) + 1
                    req_h = max(18.0, lines * 13.0 + 7.0)
                    cur_h = sum(row_heights[r : min(r + rs, num_rows)])
                    if req_h > cur_h:
                        extra = (req_h - cur_h) / rs
                        for k in range(r, min(r + rs, num_rows)):
                            row_heights[k] += extra

            table_total_h = sum(row_heights)
            avail_h = page_height - margin_bottom - cursor_y
            if cursor_y > margin_top + 15 and table_total_h > avail_h and table_total_h <= (page_height - margin_top - margin_bottom):
                current_page = doc.new_page(width=page_width, height=page_height)
                prepare_page(current_page, len(doc))
                cursor_y = margin_top
            else:
                check_overflow(min(table_total_h, 50.0))

            row_y = [cursor_y]
            for h in row_heights:
                row_y.append(row_y[-1] + h)

            # 3단계: 각 셀 BoundingBox 렌더링 (Rowspan & Colspan 100% 동일 복원)
            for c in all_cells:
                r = c.get("row", 0)
                col_idx = c.get("col", 0)
                cs = c.get("cs", 1)
                rs = c.get("rs", 1)
                c_text = c.get("text", "").strip()

                if r >= num_rows or col_idx >= num_cols:
                    continue

                x1 = col_x[col_idx]
                x2 = col_x[min(col_idx + cs, num_cols)]
                y1 = row_y[r]
                y2 = row_y[min(r + rs, num_rows)]

                cell_rect = fitz.Rect(x1, y1, x2, y2)

                # 셀 배경 채우기 (헤더 행은 단정한 연청회색, 본문은 깨끗한 흰색/아이보리)
                if r == 0:
                    fill_color = (0.92, 0.94, 0.97)
                    border_color = (0.68, 0.74, 0.82)
                    font_to_use = "malgunbd" if has_font else "ko"
                else:
                    fill_color = (1.0, 1.0, 1.0) if r % 2 == 1 else (0.985, 0.99, 1.0)
                    border_color = (0.78, 0.82, 0.88)
                    font_to_use = "malgun" if has_font else "ko"

                current_page.draw_rect(cell_rect, color=border_color, fill=fill_color, width=0.45)

                # 텍스트 수직 중앙 및 내부 여백 배치
                text_lines_cnt = c_text.count("\n") + 1
                text_h_est = text_lines_cnt * 12.0
                cell_h = y2 - y1
                y_pad = max(2.5, min((cell_h - text_h_est) / 2.0, (cell_h - 10.0) / 2.0))

                cell_w = x2 - x1
                x_pad = min(4.0, max(1.5, cell_w * 0.08))

                text_rect = fitz.Rect(
                    x1 + x_pad,
                    y1 + y_pad,
                    max(x1 + x_pad + 2.0, x2 - x_pad),
                    max(y1 + y_pad + 8.0, y2 - 1.5),
                )

                c_align = c.get("align", 0)
                if r == 0 or (len(c_text) <= 6 and "\n" not in c_text):
                    align_mode = fitz.TEXT_ALIGN_CENTER
                elif c_align == 3:
                    align_mode = fitz.TEXT_ALIGN_CENTER
                elif c_align == 2:
                    align_mode = fitz.TEXT_ALIGN_RIGHT
                else:
                    align_mode = fitz.TEXT_ALIGN_LEFT

                if c_text and text_rect.width > 2.0 and text_rect.height > 2.0:
                    current_page.insert_textbox(
                        text_rect,
                        c_text,
                        fontsize=8.5,
                        fontname=font_to_use,
                        color=(0.1, 0.12, 0.18),
                        align=align_mode,
                    )

            cursor_y = row_y[-1] + 10.0

    if not elements:
        empty_rect = fitz.Rect(margin_left, cursor_y, page_width - margin_right, cursor_y + 40)
        current_page.insert_textbox(
            empty_rect,
            "(문서에 표시할 본문 텍스트가 없습니다)",
            fontsize=11,
            fontname="malgun" if has_font else "ko",
            color=(0.5, 0.5, 0.5),
            align=fitz.TEXT_ALIGN_CENTER,
        )

    # 하단 푸터 (페이지 번호)
    total_pages = len(doc)
    for idx in range(total_pages):
        p = doc[idx]
        footer_rect = fitz.Rect(margin_left, page_height - 30, page_width - margin_right, page_height - 15)
        p.insert_textbox(
            footer_rect,
            f"- {idx + 1} / {total_pages} -",
            fontsize=8.5,
            fontname="malgun" if has_font else "ko",
            color=(0.45, 0.45, 0.45),
            align=fitz.TEXT_ALIGN_CENTER,
        )

    return doc


def load_hwp_as_fitz_doc(path: str) -> fitz.Document:
    """HWP 또는 HWPX 파일을 로드하여 PyMuPDF fitz.Document 객체로 반환."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    # 1. 한컴오피스 COM 자동화 우선 시도
    com_doc = _try_convert_via_com(path)
    if com_doc is not None:
        return com_doc

    # 2. 자체 고도화 파싱
    ext = os.path.splitext(path)[1].lower()
    if ext == ".hwpx":
        title, elements = parse_hwpx(path)
    else:
        try:
            title, elements = parse_hwp5(path)
        except Exception as e:
            try:
                title, elements = parse_hwpx(path)
            except Exception:
                raise e

    # 3. 고품질 PDF로 렌더링
    pdf_doc = render_elements_to_pdf(title, elements)
    return pdf_doc
