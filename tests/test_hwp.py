import os
import sys
import zipfile
import zlib
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hwp_loader

def test_hwpx():
    os.makedirs("sample", exist_ok=True)
    hwpx_path = "sample/test_sample.hwpx"
    with zipfile.ZipFile(hwpx_path, "w") as zf:
        zf.writestr("mimetype", "application/hwp+zip")
        content_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
        xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"
        xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">
    <hp:p><hp:run><hp:t>안녕하세요! 이것은 PDF Super Viewer에서 열람하는 HWPX 테스트 문서입니다.</hp:t></hp:run></hp:p>
    <hp:p><hp:run><hp:t>한글과컴퓨터 한컴오피스 표준 OWPML(HWPX) 형식을 완벽하게 파싱합니다.</hp:t></hp:run></hp:p>
    <hp:p><hp:run><hp:t>표 지원 테스트:</hp:t></hp:run></hp:p>
    <hp:tbl>
        <hp:tr>
            <hp:tc><hp:p><hp:run><hp:t>항목</hp:t></hp:run></hp:p></hp:tc>
            <hp:tc><hp:p><hp:run><hp:t>기존 지원</hp:t></hp:run></hp:p></hp:tc>
            <hp:tc><hp:p><hp:run><hp:t>신규 지원</hp:t></hp:run></hp:p></hp:tc>
        </hp:tr>
        <hp:tr>
            <hp:tc><hp:p><hp:run><hp:t>PDF 파일</hp:t></hp:run></hp:p></hp:tc>
            <hp:tc><hp:p><hp:run><hp:t>지원됨</hp:t></hp:run></hp:p></hp:tc>
            <hp:tc><hp:p><hp:run><hp:t>지원됨</hp:t></hp:run></hp:p></hp:tc>
        </hp:tr>
        <hp:tr>
            <hp:tc><hp:p><hp:run><hp:t>HWP/HWPX</hp:t></hp:run></hp:p></hp:tc>
            <hp:tc><hp:p><hp:run><hp:t>미지원</hp:t></hp:run></hp:p></hp:tc>
            <hp:tc><hp:p><hp:run><hp:t>완벽 지원!</hp:t></hp:run></hp:p></hp:tc>
        </hp:tr>
    </hp:tbl>
    <hp:p><hp:run><hp:t>형광펜, 메모, 도형 그리기, 텍스트 검색(Ctrl+F), 인쇄 등 모든 PDF 도구를 활용할 수 있습니다.</hp:t></hp:run></hp:p>
</hs:sec>
"""
        zf.writestr("Contents/section0.xml", content_xml)

    print("HWPX sample created.")
    doc = hwp_loader.load_hwp_as_fitz_doc(hwpx_path)
    print(f"HWPX -> PDF pages: {len(doc)}")
    page_text = doc[0].get_text()
    print(f"Extracted page 1 text:\n{page_text}")
    assert "안녕하세요" in page_text, "HWPX 텍스트 추출 실패"
    assert "HWP/HWPX" in page_text, "표 데이터 추출 실패"
    print(">>> HWPX TEST PASSED!")

def test_hwp5():
    # HWP 5.0 OLE2 파일 생성 테스트
    hwp_path = "sample/test_sample.hwp"
    
    # 1. Header (256 bytes)
    header = bytearray(256)
    header[0:17] = b"HWP Document File"
    header[32:36] = struct.pack("<I", 0x05000300) # 버전 5.0.3.0
    # flags: offset 36 (비트 0: 압축)
    flags = 0x01
    header[36:40] = struct.pack("<I", flags)
    
    # 2. Section0 데이터 (HWPTAG_PARA_HEADER(66), HWPTAG_PARA_TEXT(67))
    sec_stream = bytearray()
    
    paragraphs = [
        "이 문서는 아래아한글 HWP 5.0 바이너리 형식 테스트 문서입니다.",
        "OLE2 복합 문서 내부의 BodyText/Section0 스트림을 파싱하여 읽어옵니다.",
        "PDF Super Viewer는 HWP와 HWPX를 모두 완벽하게 읽고 주석을 달 수 있습니다."
    ]
    
    for p in paragraphs:
        # HWPTAG_PARA_HEADER (tag 66, size 0 또는 속성 크기)
        p_hdr = struct.pack("<I", 66 | (0 << 10) | (8 << 20)) + b"\x00" * 8
        sec_stream.extend(p_hdr)
        
        # HWPTAG_PARA_TEXT (tag 67)
        # UTF-16LE 바이트
        text_bytes = (p + "\r\n").encode("utf-16le")
        t_len = len(text_bytes)
        if t_len >= 0xFFF:
            t_hdr = struct.pack("<I", 67 | (0 << 10) | (0xFFF << 20)) + struct.pack("<I", t_len)
        else:
            t_hdr = struct.pack("<I", 67 | (0 << 10) | (t_len << 20))
        sec_stream.extend(t_hdr)
        sec_stream.extend(text_bytes)
        
    compressed_sec = zlib.compress(bytes(sec_stream))[2:-4] # raw deflate
    
    # OLE 파일 쓰기
    # Python 표준 라이브러리에는 OLE writer가 없으므로 간단한 OLE2 Compound File 헤더를 쓰거나
    # olefile은 읽기 전용이므로, 순수 파이썬 OLE writer를 사용
    # 여기서는 간단한 512바이트 섹터 기반 OLE2 파일을 생성합니다.
    def build_simple_ole(header_bytes, sec_bytes):
        # Sector size: 512 bytes
        # Sector 0: FileHeader (256 bytes padded to 512)
        # Sector 1..N: BodyText/Section0
        # Root Entry, Dir Entry
        # 간이 OLE 구조 생성
        sector_size = 512
        # 스트림을 4096바이트 이상으로 패딩하여 Mini FAT 대신 일반 FAT 섹터 체인을 타도록 구성
        file_hdr_len = 4096
        file_header_padded = bytes(header_bytes).ljust(file_hdr_len, b"\x00")
        hdr_sectors = file_hdr_len // sector_size # 8 sectors

        sec_padded = bytes(sec_bytes)
        sec_num_sectors = max(8, (len(sec_padded) + sector_size - 1) // sector_size)
        sec_len = sec_num_sectors * sector_size
        sec_padded = sec_padded.ljust(sec_len, b"\x00")

        dir_sector_idx = hdr_sectors + sec_num_sectors
        fat_sector_idx = dir_sector_idx + 1

        fat = [-1] * 128
        # FileHeader chain: 0..7
        for i in range(0, hdr_sectors - 1):
            fat[i] = i + 1
        fat[hdr_sectors - 1] = -2

        # Section0 chain: 8..8+sec_num_sectors-1
        sec_start = hdr_sectors
        for i in range(sec_start, sec_start + sec_num_sectors - 1):
            fat[i] = i + 1
        fat[sec_start + sec_num_sectors - 1] = -2

        fat[dir_sector_idx] = -2
        fat[fat_sector_idx] = -3

        fat_bytes = struct.pack("<128i", *fat)

        dir_data = bytearray(512)
        def write_dir_entry(offset, name, entry_type, start_sec, size, child=-1, left=-1, right=-1):
            name_u16 = name.encode("utf-16le")[:62]
            dir_data[offset:offset+len(name_u16)] = name_u16
            dir_data[offset+64:offset+66] = struct.pack("<H", len(name_u16) + 2)
            dir_data[offset+66] = entry_type # 1: Storage, 2: Stream, 5: Root
            dir_data[offset+67] = 1 # Black
            dir_data[offset+68:offset+72] = struct.pack("<i", left)
            dir_data[offset+72:offset+76] = struct.pack("<i", right)
            dir_data[offset+76:offset+80] = struct.pack("<i", child)
            dir_data[offset+116:offset+120] = struct.pack("<i", start_sec)
            dir_data[offset+120:offset+124] = struct.pack("<I", size)

        # Root Entry
        write_dir_entry(0, "Root Entry", 5, 0, 0, child=1)
        # Entry 1: FileHeader
        write_dir_entry(128, "FileHeader", 2, 0, file_hdr_len, right=2)
        # Entry 2: BodyText
        write_dir_entry(256, "BodyText", 1, 0, 0, child=3)
        # Entry 3: Section0
        write_dir_entry(384, "Section0", 2, sec_start, sec_len)
        
        # OLE Header (512 bytes)
        ole_hdr = bytearray(512)
        ole_hdr[0:8] = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" # OLE Magic
        ole_hdr[24:26] = struct.pack("<H", 0x003E)
        ole_hdr[26:28] = struct.pack("<H", 0x0003)
        ole_hdr[28:30] = struct.pack("<H", 0xFFFE) # Little-endian
        ole_hdr[30:32] = struct.pack("<H", 9) # Sector size = 512
        ole_hdr[32:34] = struct.pack("<H", 6) # Mini sector size = 64
        ole_hdr[44:48] = struct.pack("<I", 1) # Number of FAT sectors
        ole_hdr[48:52] = struct.pack("<i", dir_sector_idx) # First dir sector
        ole_hdr[56:60] = struct.pack("<I", 0) # Mini stream cutoff = 0 (모두 표준 섹터로 처리)
        ole_hdr[60:64] = struct.pack("<i", -2) # Mini FAT
        ole_hdr[64:68] = struct.pack("<I", 0) # Number of Mini FAT
        ole_hdr[68:72] = struct.pack("<i", -2) # DIFAT
        ole_hdr[72:76] = struct.pack("<I", 0) # DIFAT count
        ole_hdr[76:80] = struct.pack("<i", fat_sector_idx) # DIFAT[0]
        for i in range(1, 109):
            ole_hdr[76 + i*4:80 + i*4] = struct.pack("<i", -1)
            
        with open(hwp_path, "wb") as f:
            f.write(ole_hdr)
            f.write(file_header_padded) # sec 0
            f.write(sec_padded)         # sec 1..N
            f.write(dir_data)           # dir
            f.write(fat_bytes)          # fat
            
    build_simple_ole(header, compressed_sec)
    print("HWP 5.0 sample created.")
    
    doc = hwp_loader.load_hwp_as_fitz_doc(hwp_path)
    print(f"HWP -> PDF pages: {len(doc)}")
    page_text = doc[0].get_text()
    print(f"Extracted page 1 text:\n{page_text}")
    assert "바이너리 형식" in page_text, "HWP 텍스트 추출 실패"
    print(">>> HWP 5.0 TEST PASSED!")

if __name__ == "__main__":
    test_hwpx()
    test_hwp5()
    print("ALL TESTS PASSED SUCCESSFULLY!")
