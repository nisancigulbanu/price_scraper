from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .models import UrlRecord
from .url_cleaner import normalize_url

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def category_from_filename(path: Path) -> str:
    name = path.stem
    suffix = "_urun_listesi"
    if name.endswith(suffix):
        name = name[: -len(suffix)]
    return name.strip() or "uncategorized"


def _column_number(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref or "")
    if not match:
        return 0
    number = 0
    for char in match.group(1):
        number = number * 26 + ord(char) - 64
    return number - 1


def read_xlsx_urls(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", NS):
                shared_strings.append("".join(t.text or "" for t in item.findall(".//a:t", NS)))

        sheet_name = "xl/worksheets/sheet1.xml"
        root = ET.fromstring(archive.read(sheet_name))
        rows: list[list[str | None]] = []
        for row in root.findall(".//a:sheetData/a:row", NS):
            values: list[str | None] = []
            for cell in row.findall("a:c", NS):
                value_node = cell.find("a:v", NS)
                if value_node is None:
                    continue
                value = value_node.text or ""
                if cell.get("t") == "s":
                    value = shared_strings[int(value)]
                index = _column_number(cell.get("r", "A"))
                while len(values) <= index:
                    values.append(None)
                values[index] = value
            rows.append(values)

    urls: list[str] = []
    for row in rows:
        for value in row:
            if isinstance(value, str) and value.strip().lower().startswith(("http://", "https://", "www.")):
                normalized = normalize_url(value)
                if normalized:
                    urls.append(normalized)
    return urls


def read_input_records(input_path: Path) -> list[UrlRecord]:
    if input_path.is_dir():
        return read_category_directory(input_path)
    suffix = input_path.suffix.lower()
    if suffix == ".xlsx":
        category = category_from_filename(input_path)
        return [
            UrlRecord(source_file=input_path.name, category=category, url=url)
            for url in read_xlsx_urls(input_path)
        ]
    if suffix in {".txt", ".csv"}:
        category = category_from_filename(input_path)
        records: list[UrlRecord] = []
        for line in input_path.read_text(encoding="utf-8-sig").splitlines():
            normalized = normalize_url(line.split(",")[-1].strip())
            if normalized:
                records.append(UrlRecord(source_file=input_path.name, category=category, url=normalized))
        return records
    raise ValueError(f"Unsupported input type: {input_path}")


def read_category_directory(directory: Path) -> list[UrlRecord]:
    records: list[UrlRecord] = []
    for path in sorted(directory.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        category = category_from_filename(path)
        for url in read_xlsx_urls(path):
            records.append(UrlRecord(source_file=path.name, category=category, url=url))
    return records
