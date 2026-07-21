from __future__ import annotations

import argparse
from pathlib import Path

from .config import settings
from .repository import backfill_unit_prices, create_job, ensure_database, import_input, list_urls
from .scraper import run_scrape_job
from .storage import export_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-site price tracker")
    parser.add_argument("--serve", action="store_true", help="Start the local web application")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--input", default=str(settings.categories_dir), help="Input file or category directory")
    parser.add_argument("--output", default=str(settings.output_dir / "prices.xlsx"), help="XLSX output path")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--domain", default=None)
    parser.add_argument("--category-id", type=int, default=None)
    parser.add_argument("--only-failed", action="store_true", help="Reserved for retrying failed URLs")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--import-categories", action="store_true", help="Only import category URL files")
    parser.add_argument("--backfill-unit-prices", action="store_true", help="Fill quantity and unit price fields for existing results")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    ensure_database(settings.database_path)

    if args.serve:
        backfill_unit_prices(settings.database_path)
        import uvicorn

        uvicorn.run("price_tracker.web.app:app", host=args.host, port=args.port, reload=False)
        return

    input_path = Path(args.input)
    imported = import_input(input_path, settings.database_path)
    print(f"Imported {imported} new URLs from {input_path}")

    if args.import_categories:
        return

    if args.backfill_unit_prices:
        updated = backfill_unit_prices(settings.database_path)
        print(f"Backfilled unit prices for {updated} results")
        return

    urls = list_urls(
        settings.database_path,
        category_id=args.category_id,
        domain=args.domain,
        limit=args.limit,
    )
    job_id = create_job(
        settings.database_path,
        scope="cli",
        category_id=args.category_id,
        total=len(urls),
    )
    run_scrape_job(
        db_path=settings.database_path,
        job_id=job_id,
        category_id=args.category_id,
        limit=args.limit,
        domain=args.domain,
        delay_seconds=0.0 if args.debug else 1.5,
    )
    output = export_reports(settings.database_path, Path(args.output))
    print(f"Exported report to {output}")


if __name__ == "__main__":
    main()
