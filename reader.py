"""PDF text extraction and audiobook preparation, independent of Streamlit."""

from __future__ import annotations

import re
from collections import Counter

import fitz


CAPTION = re.compile(r"^\s*(?:fig(?:ura|ure|\.)?|imagen|gr[aá]f(?:ico|ica)|tabla|table)\s*(?:\d+|[IVX]+)[\s.:\-–]", re.I)
PAGE_NUMBER = re.compile(r"^\s*(?:p[aá]g(?:ina|\.)?\s*)?\d{1,4}\s*$", re.I)


def page_count(pdf: bytes) -> int:
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        return len(doc)


def _lines(page, top: float, bottom: float, skip_captions: bool):
    lines = []
    for block in page.get_text("dict", sort=True)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            y0, y1 = line["bbox"][1], line["bbox"][3]
            if y0 < top or y1 > bottom:
                continue
            value = " ".join(s["text"] for s in line["spans"]).strip()
            value = re.sub(r"\s+", " ", value)
            if value and not (skip_captions and CAPTION.match(value)):
                lines.append((value, y0, y1))
    return lines


def extract_pdf(
    pdf: bytes,
    first_page: int = 1,
    last_page: int | None = None,
    excluded_pages: set[int] | None = None,
    top_percent: int = 7,
    bottom_percent: int = 7,
    skip_captions: bool = True,
    skip_repeated: bool = True,
) -> str:
    """Extract editable body text. Page numbers are 1 based, inclusive."""
    excluded_pages = excluded_pages or set()
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        end = min(last_page or len(doc), len(doc))
        if not 1 <= first_page <= end:
            raise ValueError("El intervalo de páginas no es válido.")
        pages = []
        edge_counts: Counter[str] = Counter()
        for number in range(first_page, end + 1):
            if number in excluded_pages:
                continue
            page = doc[number - 1]
            top = page.rect.height * top_percent / 100
            bottom = page.rect.height * (100 - bottom_percent) / 100
            if top >= bottom:
                raise ValueError("Los márgenes dejan la página sin espacio de lectura.")
            lines = _lines(page, top, bottom, skip_captions)
            pages.append(lines)
            edge_values = set()
            for value, y0, y1 in lines:
                if y0 < page.rect.height * .17 or y1 > page.rect.height * .83:
                    edge_values.add(value.casefold())
            edge_counts.update(edge_values)

        repeated = {line for line, count in edge_counts.items() if count >= 2 and len(line) < 110}
        pieces = []
        for lines in pages:
            kept = [value for value, _, _ in lines
                    if not PAGE_NUMBER.fullmatch(value)
                    and not (skip_repeated and value.casefold() in repeated)]
            if kept:
                text = "\n".join(kept)
                text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
                pieces.append(text)
        return "\n\n".join(pieces).strip()


def chunks(text: str, max_chars: int = 2200) -> list[str]:
    """Split by paragraphs/sentences while preserving every nonspace character."""
    paragraphs = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n\s*\n", text)]
    result: list[str] = []
    for paragraph in filter(None, paragraphs):
        sentences = re.split(r"(?<=[.!?;:])\s+", paragraph)
        current = ""
        for sentence in sentences:
            while len(sentence) > max_chars:
                cut = sentence.rfind(" ", 0, max_chars + 1)
                cut = cut if cut > max_chars // 2 else max_chars
                part, sentence = sentence[:cut], sentence[cut:].lstrip()
                if current:
                    result.append(current)
                    current = ""
                result.append(part.strip())
            if not sentence:
                continue
            if current and len(current) + 1 + len(sentence) > max_chars:
                result.append(current)
                current = ""
            current = f"{current} {sentence}" if current else sentence
        if current:
            result.append(current)
    return result
