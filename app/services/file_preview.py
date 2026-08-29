from __future__ import annotations

import csv
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
import io
import re
import zipfile
import xml.etree.ElementTree as ET


MAX_PREVIEW_CHARS = 4000
XML_TEXT_PATTERN = re.compile(r"\s+")
RTF_CONTROL_PATTERN = re.compile(r"\\[a-zA-Z]+\d* ?|\\.|[{}]")


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


def html_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str:
    parser = _VisibleTextParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    return parser.text()[:limit]


def xml_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str:
    try:
        return _xml_text(data)[:limit]
    except ET.ParseError:
        return text_preview(data, limit)


def rtf_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str:
    text = data.decode("utf-8", errors="replace")
    stripped = RTF_CONTROL_PATTERN.sub(" ", text)
    return XML_TEXT_PATTERN.sub(" ", stripped).strip()[:limit]


def email_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str:
    message = BytesParser(policy=policy.default).parsebytes(data)
    parts = []
    if message["subject"]:
        parts.append(f"Subject: {message['subject']}")
    body = message.get_body(preferencelist=("plain", "html"))
    if body is not None:
        content = body.get_content()
        if body.get_content_type() == "text/html":
            content = html_preview(content.encode("utf-8"), limit)
        parts.append(str(content))
    return "\n\n".join(parts)[:limit]


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


def opendocument_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str | None:
    xml = _read_zip_member(data, "content.xml")
    if xml is None:
        return None
    try:
        return _xml_text(xml)[:limit] or None
    except ET.ParseError:
        return None


def epub_preview(data: bytes, limit: int = MAX_PREVIEW_CHARS) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            parts = []
            for name in archive.namelist():
                if name.lower().endswith((".html", ".xhtml", ".htm")):
                    parts.append(html_preview(archive.read(name), limit))
                if len("\n".join(parts)) >= limit:
                    break
            preview = "\n".join(part for part in parts if part)
            return preview[:limit] or None
    except zipfile.BadZipFile:
        return None


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._hidden_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and not self._hidden_depth:
            self._parts.append(text)

    def text(self) -> str:
        return "\n".join(self._parts)


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
