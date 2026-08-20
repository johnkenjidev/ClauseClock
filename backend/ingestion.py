"""
Contract ingestion — Stage 1.

Two responsibilities:
  1. Store / read / hard-delete original uploaded files in MongoDB GridFS.
     GridFS is chosen over external object storage because Stage 1 requires a
     REAL hard deletion path for stored originals, and GridFS supports
     `bucket.delete(...)` while remaining persistent with the database.
  2. Extract readable text from PDF (pdfplumber) and DOCX (python-docx),
     preserving source-location markers (PDF page numbers; DOCX section /
     heading / paragraph markers) so extracted text can be traced back.

No AI, no chunking-for-analysis, no clause detection — that is Stage 2+.
"""

import hashlib
import io

import pdfplumber
from bson import ObjectId
from docx import Document as DocxDocument
from docx.document import Document as _DocxDocumentType
from docx.oxml.ns import qn
from docx.table import Table as _DocxTable
from docx.text.paragraph import Paragraph as _DocxParagraph
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

# A document is treated as unreadable/image-based below this many chars/page.
SCANNED_CHARS_PER_PAGE = 100
SCANNED_MESSAGE = (
    "This looks like a scanned or image-based PDF. ClauseClock cannot read it "
    "yet. Upload a text-based version."
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# GridFS original-file storage
# --------------------------------------------------------------------------
async def store_original(bucket: AsyncIOMotorGridFSBucket, data: bytes,
                         filename: str, mime_type: str) -> str:
    file_id = await bucket.upload_from_stream(
        filename, io.BytesIO(data), metadata={"mime_type": mime_type}
    )
    return str(file_id)


async def read_original(bucket: AsyncIOMotorGridFSBucket, storage_key: str) -> bytes:
    stream = await bucket.open_download_stream(ObjectId(storage_key))
    return await stream.read()


async def delete_original(bucket: AsyncIOMotorGridFSBucket, storage_key: str) -> None:
    """Hard delete the stored original. Absent files are ignored."""
    try:
        await bucket.delete(ObjectId(storage_key))
    except Exception:
        # File already gone / invalid key — deletion is still satisfied.
        pass


# --------------------------------------------------------------------------
# PDF extraction (pdfplumber) — page-number markers + tables
# --------------------------------------------------------------------------
def _extract_pdf(data: bytes) -> tuple[str, int]:
    parts: list[str] = []
    page_count = 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page_count = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            parts.append(f"\n========== Page {i} ==========\n")
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text)
            # Tables rendered as pipe-delimited rows, tagged with the page.
            try:
                for t_idx, table in enumerate(page.extract_tables() or [], start=1):
                    if not table:
                        continue
                    parts.append(f"\n[Table {t_idx} · Page {i}]")
                    for row in table:
                        cells = [(c or "").replace("\n", " ").strip() for c in row]
                        parts.append(" | ".join(cells))
            except Exception:
                pass
    return "\n".join(parts).strip(), page_count


# --------------------------------------------------------------------------
# DOCX extraction (python-docx) — section/heading/paragraph markers + tables
# --------------------------------------------------------------------------
def _iter_block_items(parent):
    """Yield paragraphs and tables in document order."""
    if isinstance(parent, _DocxDocumentType):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._tc
    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield _DocxParagraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield _DocxTable(child, parent)


def _extract_docx(data: bytes) -> tuple[str, int]:
    doc = DocxDocument(io.BytesIO(data))
    parts: list[str] = []
    current_section = "(preamble)"
    para_idx = 0
    table_idx = 0

    for block in _iter_block_items(doc):
        if isinstance(block, _DocxParagraph):
            text = block.text.strip()
            if not text:
                continue
            para_idx += 1
            style = (block.style.name or "") if block.style else ""
            if style.lower().startswith("heading") or style.lower() == "title":
                current_section = text
                parts.append(f"\n[§ {text}]  [loc: heading, ¶{para_idx}]")
            else:
                parts.append(f"¶{para_idx} | {text}  [loc: {current_section}]")
        elif isinstance(block, _DocxTable):
            table_idx += 1
            parts.append(f"\n[Table {table_idx} · §{current_section}]")
            for row in block.rows:
                cells = [c.text.replace("\n", " ").strip() for c in row.cells]
                parts.append(" | ".join(cells))

    # DOCX has no reliable page count; paragraph markers carry the location.
    return "\n".join(parts).strip(), None


def extract_text(data: bytes, file_type: str) -> tuple[str, int | None]:
    """Return (raw_text, page_count). page_count is None for DOCX."""
    if file_type == "pdf":
        return _extract_pdf(data)
    if file_type == "docx":
        return _extract_docx(data)
    raise ValueError(f"Unsupported file_type: {file_type}")


def is_scanned(raw_text: str, page_count: int | None) -> bool:
    """
    True when the document reads as image-based (under 100 chars/page).
    For DOCX (page_count None) fall back to a flat 100-char floor.
    """
    n = len((raw_text or "").strip())
    if page_count and page_count > 0:
        return n < SCANNED_CHARS_PER_PAGE * page_count
    return n < SCANNED_CHARS_PER_PAGE
