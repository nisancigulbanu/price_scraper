from __future__ import annotations

import zipfile
from pathlib import Path

from price_tracker.category_importer import category_from_filename, read_xlsx_urls


def _write_minimal_xlsx(path: Path, values: list[str]) -> None:
    shared_items = "".join(f"<si><t>{value}</t></si>" for value in values)
    rows = "".join(
        f'<row r="{index + 1}"><c r="A{index + 1}" t="s"><v>{index}</v></c></row>'
        for index, _ in enumerate(values)
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">{shared_items}</sst>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{rows}</sheetData></worksheet>',
        )


def test_category_name_comes_from_filename():
    assert category_from_filename(Path("500_ml_elma_sirkesi_urun_listesi.xlsx")) == "500_ml_elma_sirkesi"


def test_read_xlsx_urls_reads_single_url_column(tmp_path):
    path = tmp_path / "bal_urun_listesi.xlsx"
    _write_minimal_xlsx(path, ["URL", "https://example.com/a?utm_source=x", "not url"])
    assert read_xlsx_urls(path) == ["https://example.com/a"]
