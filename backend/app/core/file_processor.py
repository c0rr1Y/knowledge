"""Universal document processor: supports PDF, Word, Excel, PPT, Markdown, TXT, HTML, images."""

import os
from typing import Optional


# ---- Format-specific extractors ----

def _read_text_auto(file_path: str) -> str:
    """Read a text file, trying common Chinese encodings before falling back."""
    with open(file_path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", errors="ignore")


def extract_text_txt(file_path: str) -> list[dict]:
    """Plain text / Markdown files (any common encoding)."""
    text = _read_text_auto(file_path)
    if not text.strip():
        return []
    return [{"page": 1, "text": text.strip(), "title": os.path.basename(file_path)}]


def extract_text_docx(file_path: str) -> list[dict]:
    """Word .docx files — extracts body paragraphs AND table cells."""
    from docx import Document as DocxDoc

    try:
        doc = DocxDoc(file_path)
        parts = []

        for p in doc.paragraphs:
            if p.text.strip():
                parts.append(p.text.strip())

        # Tables hold the real content in checklists / adaptation docs.
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                if any(cells):
                    parts.append(" | ".join(cells))

        if parts:
            return [{"page": 1, "text": "\n".join(parts), "title": os.path.basename(file_path)}]
    except Exception as e:
        print(f"[DocParser] python-docx failed: {e}")

    # Fallback: raw text extraction for legacy/odd files
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        import re
        text = data.decode("utf-8", errors="ignore")
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 10 and not any(c in l for c in ['\\x', '\x00'])]
        if lines:
            return [{"page": 1, "text": "\n".join(lines[:500]), "title": os.path.basename(file_path)}]
    except Exception:
        pass

    raise ValueError(f"Cannot read this Word document. It may be an old .doc format or contain only images.")


# ---- Legacy .doc / .ppt -> modern format via MS Office COM ----

def _office_convert(src_path: str, dst_path: str, app: str) -> None:
    """Convert .doc/.ppt to .docx/.pptx (LibreOffice preferred, MS Office COM fallback)."""
    import shutil

    src_path = os.path.abspath(src_path)
    dst_path = os.path.abspath(dst_path)

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        _convert_via_libreoffice(soffice, src_path, dst_path)
        return

    _convert_via_com(src_path, dst_path, app)


def _convert_via_libreoffice(soffice: str, src_path: str, dst_path: str) -> None:
    import subprocess
    import tempfile

    target_ext = os.path.splitext(dst_path)[1]  # ".docx" / ".pptx"
    out_dir = tempfile.mkdtemp(prefix="rag_conv_")
    cmd = [soffice, "--headless", "--convert-to", target_ext.lstrip("."), "--outdir", out_dir, src_path]
    result = subprocess.run(cmd, capture_output=True, timeout=180)
    if result.returncode != 0:
        raise ValueError(f"LibreOffice 转换失败: {result.stderr.decode(errors='ignore')[:200]}")

    base = os.path.splitext(os.path.basename(src_path))[0]
    converted = os.path.join(out_dir, base + target_ext)
    if not os.path.exists(converted):
        raise ValueError("LibreOffice 未生成转换文件")
    import shutil as _shutil
    _shutil.move(converted, dst_path)


def _convert_via_com(src_path: str, dst_path: str, app: str) -> None:
    """Convert .doc/.ppt via MS Office COM automation (Windows only)."""
    import pythoncom
    import win32com.client

    src_path = os.path.abspath(src_path)
    dst_path = os.path.abspath(dst_path)

    co_initialized = False
    try:
        pythoncom.CoInitialize()
        co_initialized = True
    except Exception:
        pass  # already initialized on this thread

    app_obj = None
    try:
        if app == "word":
            app_obj = win32com.client.DispatchEx("Word.Application")
            app_obj.Visible = False
            app_obj.DisplayAlerts = 0
            try:
                app_obj.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
            except Exception:
                pass
            doc = app_obj.Documents.Open(src_path, ReadOnly=True, ConfirmConversions=False)
            try:
                doc.SaveAs2(dst_path, FileFormat=16)  # wdFormatXMLDocument = .docx
            finally:
                doc.Close(False)
        elif app == "powerpoint":
            app_obj = win32com.client.DispatchEx("PowerPoint.Application")
            pres = app_obj.Presentations.Open(src_path, ReadOnly=True, WithWindow=False)
            try:
                pres.SaveAs(dst_path, 24)  # ppSaveAsOpenXMLPresentation = .pptx
            finally:
                pres.Close()
        else:
            raise ValueError(f"未知的转换类型: {app}")
    finally:
        if app_obj is not None:
            try:
                app_obj.Quit()
            except Exception:
                pass
        if co_initialized:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def _convert_then_extract(src_path: str, app: str, extractor) -> list[dict]:
    """Convert a legacy Office file, extract text, then clean up the temp file."""
    import tempfile
    import uuid

    target_ext = ".docx" if app == "word" else ".pptx"
    dst = os.path.join(tempfile.gettempdir(), f"rag_{uuid.uuid4().hex}{target_ext}")
    try:
        _office_convert(src_path, dst, app)
        if not os.path.exists(dst) or os.path.getsize(dst) == 0:
            raise ValueError("转换失败：Office 未生成有效文件")
        return extractor(dst)
    finally:
        if os.path.exists(dst):
            try:
                os.remove(dst)
            except Exception:
                pass


def _get_tesseract_cmd() -> str:
    """Return the Tesseract executable path (config -> auto-detect -> default)."""
    import shutil
    from app.config import settings
    if getattr(settings, "tesseract_cmd", ""):
        return settings.tesseract_cmd
    found = shutil.which("tesseract")
    if found:
        return found
    default = r"D:\tools\TesseractOCR\tesseract.exe"
    if os.path.exists(default):
        return default
    return "tesseract"


def extract_text_doc(file_path: str) -> list[dict]:
    """Legacy .doc — convert to .docx, then parse."""
    return _convert_then_extract(file_path, "word", extract_text_docx)


def extract_text_ppt(file_path: str) -> list[dict]:
    """Legacy .ppt — convert to .pptx, then parse."""
    return _convert_then_extract(file_path, "powerpoint", extract_text_pptx)


def _looks_numeric(value) -> bool:
    s = str(value).strip().replace(",", "").replace("¥", "").replace("￥", "").replace("%", "")
    if not s:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def _rows_to_pages(rows: list[tuple], sheet_name: str, basename: str) -> list[dict]:
    """Convert raw sheet rows into small header+row-group pages.

    Each page repeats the header and stays within the embedding window so every
    row is retrievable for aggregation queries.
    """
    if not rows:
        return []
    header_line = " | ".join(str(c) if c is not None else "" for c in rows[0]).strip()
    header_prefix = f"## Sheet: {sheet_name}\n表头: {header_line}"
    data_rows = rows[1:]

    if not data_rows:
        return [{"text": header_prefix, "title": f"{basename} - {sheet_name}"}]

    rows_budget = max(150, 450 - len(header_prefix))
    pages: list[dict] = []
    group_lines: list[str] = []
    group_chars = 0
    group_start = 1

    for idx, row in enumerate(data_rows, start=1):
        row_line = " | ".join(str(c) if c is not None else "" for c in row)
        row_cost = len(row_line) + 1
        if group_lines and group_chars + row_cost > rows_budget:
            pages.append({
                "text": header_prefix + "\n" + "\n".join(group_lines),
                "title": f"{basename} - {sheet_name} (行 {group_start}-{idx - 1})",
            })
            group_lines = []
            group_chars = 0
            group_start = idx
        group_lines.append(row_line)
        group_chars += row_cost

    if group_lines:
        pages.append({
            "text": header_prefix + "\n" + "\n".join(group_lines),
            "title": f"{basename} - {sheet_name} (行 {group_start}-{len(data_rows)})",
        })
    return pages


def extract_text_xlsx(file_path: str) -> list[dict]:
    """Excel .xlsx files."""
    import openpyxl
    wb = openpyxl.load_workbook(file_path, data_only=True)
    results = []
    basename = os.path.basename(file_path)

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = [r for r in ws.iter_rows(values_only=True) if any(c is not None and str(c).strip() for c in r)]
        for page in _rows_to_pages(rows, sheet_name, basename):
            page["page"] = len(results) + 1
            results.append(page)

    return results if results else [{"page": 1, "text": "(空表格)", "title": basename}]


def extract_text_xls(file_path: str) -> list[dict]:
    """Excel .xls files (old binary format) via xlrd."""
    import xlrd
    wb = xlrd.open_workbook(file_path)
    results = []
    basename = os.path.basename(file_path)

    for sheet in wb.sheets():
        rows = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
        rows = [r for r in rows if any(c not in (None, "") and str(c).strip() for c in r)]
        for page in _rows_to_pages(rows, sheet.name, basename):
            page["page"] = len(results) + 1
            results.append(page)

    return results if results else [{"page": 1, "text": "(空表格)", "title": basename}]


def extract_text_csv(file_path: str) -> list[dict]:
    """CSV files - parse with the csv module (handles quoted fields)."""
    import csv
    import io
    text = _read_text_auto(file_path)
    rows = [r for r in csv.reader(io.StringIO(text)) if any(c and str(c).strip() for c in r)]
    if not rows:
        return [{"page": 1, "text": "(空表格)", "title": os.path.basename(file_path)}]

    basename = os.path.basename(file_path)
    # If the first row looks like data (contains numbers), synthesize a header.
    if any(_looks_numeric(c) for c in rows[0]):
        ncols = max(len(r) for r in rows)
        rows = [[f"列{i+1}" for i in range(ncols)]] + rows

    results = []
    for page in _rows_to_pages(rows, "CSV", basename):
        page["page"] = len(results) + 1
        results.append(page)
    return results


def extract_text_pptx(file_path: str) -> list[dict]:
    """PowerPoint .pptx files (old .ppt binary not supported — convert to .pptx)."""
    from pptx import Presentation
    try:
        prs = Presentation(file_path)
    except Exception:
        raise ValueError("无法读取此 PowerPoint 文件，可能是旧版 .ppt 二进制格式，请用 PowerPoint 另存为 .pptx 后再上传。")
    results = []

    for i, slide in enumerate(prs.slides):
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    if paragraph.text.strip():
                        texts.append(paragraph.text.strip())
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if any(cells):
                        texts.append(" | ".join(cells))
        if texts:
            results.append({
                "page": i + 1,
                "text": "\n".join(texts),
                "title": f"Slide {i + 1}",
            })

    return results if results else [{"page": 1, "text": "(no text in presentation)", "title": os.path.basename(file_path)}]


def extract_text_html(file_path: str) -> list[dict]:
    """HTML files - extract text content (auto-detect encoding)."""
    from bs4 import BeautifulSoup
    with open(file_path, "rb") as f:
        content = f.read()
    soup = BeautifulSoup(content, "html.parser")
    # Remove scripts and styles
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return []
    return [{"page": 1, "text": "\n".join(lines), "title": os.path.basename(file_path)}]


def extract_text_image(file_path: str) -> list[dict]:
    """Image files - OCR with Tesseract, plus image description for LLM context."""
    import pytesseract
    from PIL import Image

    # Point to the user's Tesseract installation
    pytesseract.pytesseract.tesseract_cmd = _get_tesseract_cmd()

    img = Image.open(file_path)

    # Try Tesseract OCR first
    try:
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
    except Exception:
        text = ""

    # Also provide image metadata for context
    meta = f"[Image: {os.path.basename(file_path)}, size: {img.size[0]}x{img.size[1]}]"
    full_text = f"{meta}\n{text}" if text.strip() else meta

    return [{"page": 1, "text": full_text, "title": os.path.basename(file_path)}]


# ---- PDF ----

def _ocr_pdf_page(page, page_num: int) -> str:
    """OCR a PDF page (scanned / image-only pages) and return extracted text."""
    import fitz
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = _get_tesseract_cmd()
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return pytesseract.image_to_string(img, lang="chi_sim+eng").strip()
    except Exception as e:
        print(f"[PDF OCR] page {page_num + 1} failed: {e}")
        return ""


def extract_text_pdf(file_path: str) -> list[dict]:
    """Extract text from PDF using PyMuPDF; OCR any image-only pages."""
    import fitz
    doc = fitz.open(file_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()

        if not text:
            text = _ocr_pdf_page(page, page_num)

        if text:
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            title = lines[0] if lines else f"Page {page_num + 1}"
            pages.append({
                "page": page_num + 1,
                "text": text,
                "title": title,
            })

    doc.close()
    return pages


# ---- File-type router ----

# Map extensions to extractor functions
EXTRACTORS = {
    ".pdf": extract_text_pdf,
    ".docx": extract_text_docx,
    ".doc": extract_text_doc,
    ".txt": extract_text_txt,
    ".md": extract_text_txt,
    ".markdown": extract_text_txt,
    ".rst": extract_text_txt,
    ".xlsx": extract_text_xlsx,
    ".xls": extract_text_xls,
    ".csv": extract_text_csv,
    ".pptx": extract_text_pptx,
    ".ppt": extract_text_ppt,
    ".html": extract_text_html,
    ".htm": extract_text_html,
    ".png": extract_text_image,
    ".jpg": extract_text_image,
    ".jpeg": extract_text_image,
    ".bmp": extract_text_image,
    ".gif": extract_text_image,
    ".webp": extract_text_image,
    ".tiff": extract_text_image,
    ".tif": extract_text_image,
}

ALLOWED_EXTENSIONS = set(EXTRACTORS.keys())


def get_extractor(file_path: str):
    """Get the right extractor function for a file."""
    ext = os.path.splitext(file_path)[1].lower()
    return EXTRACTORS.get(ext)


# ---- Semantic chunking ----

def _split_long_paragraph(para: str, max_chars: int) -> list[str]:
    """Split a long paragraph into units <= max_chars.

    Prefers newline boundaries (keeps table rows / list items intact), then
    hard-splits any remaining over-long line by characters.
    """
    units = []
    for line in para.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) <= max_chars:
            units.append(line)
        else:
            units.extend(line[i:i + max_chars] for i in range(0, len(line), max_chars))
    return units


def semantic_chunk(text: str, max_chars: int = 500, overlap_chars: int = 50) -> list[str]:
    """Split text into chunks that fit the embedding window.

    bge-large-zh-v1.5 truncates inputs beyond ~512 tokens, so chunks larger than
    ~500 chars lose their tail during embedding and become unsearchable. Keeping
    chunks small (and splitting tables by row) is what makes aggregation queries
    see complete data.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    units: list[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            units.append(para)
        else:
            units.extend(_split_long_paragraph(para, max_chars))

    chunks: list[str] = []
    current = ""
    for unit in units:
        if not current:
            current = unit
        elif len(current) + len(unit) + 2 <= max_chars:
            current += "\n\n" + unit
        else:
            chunks.append(current)
            room = max_chars - len(unit) - 2
            if overlap_chars > 0 and room > 0:
                current = current[-min(overlap_chars, room):] + "\n\n" + unit
            else:
                current = unit

    if current:
        chunks.append(current)

    return [c for c in chunks if len(c) >= 20]


# ---- Main processing API ----

def process_file(file_path: str, max_chunk_chars: int = 500, overlap_chars: int = 50) -> list[dict]:
    """Route to the right extractor, then chunk the result."""
    ext = os.path.splitext(file_path)[1].lower()
    extractor = EXTRACTORS.get(ext)

    if extractor is None:
        raise ValueError(f"Unsupported file format: {ext}. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    pages = extractor(file_path)

    all_chunks = []
    for page_data in pages:
        page_chunks = semantic_chunk(
            page_data["text"],
            max_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
        )
        for chunk_text in page_chunks:
            all_chunks.append({
                "index": len(all_chunks),
                "text": chunk_text,
                "page": page_data.get("page", 1),
                "title": page_data.get("title", ""),
            })

    return all_chunks


# Legacy alias for backward compat
def process_pdf(file_path: str, max_chunk_chars: int = 500, overlap_chars: int = 50) -> list[dict]:
    """Process PDF - kept for backward compatibility, calls universal process_file."""
    return process_file(file_path, max_chunk_chars, overlap_chars)
