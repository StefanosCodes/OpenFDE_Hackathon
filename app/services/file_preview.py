from __future__ import annotations

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET


MAX_PREVIEW_CHARS = 4000
XML_TEXT_PATTERN = re.compile(r"\s+")


def text_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str:
    return data.decode("utf-8", errors="replace")[:limit]


def csv_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str:
    text = data.decode("utf-8", errors="replace")
    rows = []
    reader = csv.reader(io.StringIO(text))
    for index, row in enumerate(reader):
        rows.append(" | ".join(cell.strip() for cell in row))
        if index >= 24:
            break
    return "\n".join(rows)[:limit]


def docx_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str | None:
    xml = _read_zip_member(data, "word/document.xml")
    if xml is None:
        return None
    return _xml_text(xml)[:limit] or None


def xlsx_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            shared_strings = _xlsx_shared_strings(archive)
            sheet_names = sorted(
                name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            )
            lines = []
            for sheet_name in sheet_names[:3]:
                lines.append(f"[{sheet_name}]")
                lines.extend(_xlsx_sheet_rows(archive.read(sheet_name), shared_strings)[:20])
            preview = "\n".join(lines)
            return preview[:limit] or None
    except (KeyError, ET.ParseError, zipfile.BadZipFile):
        return None


def pptx_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            slide_names = sorted(
                name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            )
            chunks = []
            for index, slide_name in enumerate(slide_names[:20], start=1):
                text = _xml_text(archive.read(slide_name))
                if text:
                    chunks.append(f"Slide {index}: {text}")
            preview = "\n".join(chunks)
            return preview[:limit] or None
    except (ET.ParseError, zipfile.BadZipFile):
        return None


def _read_zip_member(data: bytes, member: str) -> bytes | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return archive.read(member)
    except (KeyError, zipfile.BadZipFile):
        return None


def _xml_text(xml: bytes) -> str:
    root = ET.fromstring(xml)
    parts = []
    for element in root.iter():
        if element.text:
            text = XML_TEXT_PATTERN.sub(" ", element.text).strip()
            if text:
                parts.append(text)
    return "\n".join(parts)


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [_xml_text(ET.tostring(item, encoding="utf-8")) for item in root]


def _xlsx_sheet_rows(xml: bytes, shared_strings: list[str]) -> list[str]:
    root = ET.fromstring(xml)
    rows = []
    for row in root.iter():
        if not row.tag.endswith("row"):
            continue
        values = []
        for cell in row:
            if not cell.tag.endswith("c"):
                continue
            cell_type = cell.attrib.get("t")
            value = None
            for child in cell:
                if child.tag.endswith("v") and child.text is not None:
                    value = child.text
                    break
            if value is None:
                continue
            if cell_type == "s":
                try:
                    value = shared_strings[int(value)]
                except (ValueError, IndexError):
                    pass
            values.append(value)
        if values:
            rows.append(" | ".join(values))
    return rows
