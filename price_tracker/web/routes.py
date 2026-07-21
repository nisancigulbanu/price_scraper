from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..analytics import price_stats, status_summary, unit_price_stats
from ..config import settings
from ..repository import (
    add_url,
    clear_results,
    create_job,
    distinct_domains,
    get_category,
    get_job,
    import_input,
    latest_job,
    latest_results,
    list_categories,
    list_urls,
    upsert_category,
)
from ..scraper import run_scrape_job
from ..url_cleaner import normalize_url
from ..db import connect

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _db_path(request: Request) -> Path:
    return request.app.state.db_path


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, category_id: int | None = None) -> HTMLResponse:
    db_path = _db_path(request)
    categories = list_categories(db_path)
    results = latest_results(db_path, category_id=category_id, limit=1000)
    selected_category = get_category(db_path, category_id) if category_id else None
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "categories": categories,
            "selected_category": selected_category,
            "results": results[:100],
            "stats": price_stats(results),
            "unit_stats": unit_price_stats(results),
            "status_summary": status_summary(results),
            "job": latest_job(db_path),
            "domains": distinct_domains(db_path),
        },
    )


@router.get("/results", response_class=HTMLResponse)
def results(
    request: Request,
    category_id: int | None = None,
    status: str | None = None,
    domain: str | None = None,
) -> HTMLResponse:
    db_path = _db_path(request)
    rows = latest_results(db_path, category_id=category_id, status=status, domain=domain, limit=2000)
    return templates.TemplateResponse(
        request,
        "results.html",
        {
            "categories": list_categories(db_path),
            "domains": distinct_domains(db_path),
            "rows": rows,
            "stats": price_stats(rows),
            "unit_stats": unit_price_stats(rows),
            "selected_category_id": category_id,
            "selected_status": status or "",
            "selected_domain": domain or "",
        },
    )


@router.get("/add-url", response_class=HTMLResponse)
def add_url_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "add_url.html",
        {"categories": list_categories(_db_path(request)), "message": None, "error": None},
    )


@router.post("/add-url", response_class=HTMLResponse)
def add_url_submit(
    request: Request,
    category_mode: str = Form(...),
    category_id: int | None = Form(None),
    new_category: str = Form(""),
    urls: str = Form(...),
) -> HTMLResponse:
    db_path = _db_path(request)
    error = None
    message = None
    normalized_urls = [normalize_url(line.strip()) for line in urls.splitlines() if line.strip()]
    normalized_urls = [url for url in normalized_urls if url]
    if not normalized_urls:
        error = "Gecerli URL bulunamadi."
    else:
        with connect(db_path) as conn:
            if category_mode == "new":
                category_name = new_category.strip()
                if not category_name:
                    error = "Yeni kategori adi gerekli."
                    category_db_id = None
                else:
                    category_db_id = upsert_category(conn, category_name, "web")
            else:
                category_db_id = category_id
                if category_db_id is None:
                    error = "Kategori secimi gerekli."

            if error is None and category_db_id is not None:
                before = conn.execute("SELECT COUNT(*) AS count FROM urls").fetchone()["count"]
                for url in normalized_urls:
                    add_url(conn, int(category_db_id), url)
                after = conn.execute("SELECT COUNT(*) AS count FROM urls").fetchone()["count"]
                message = f"{int(after) - int(before)} yeni URL kaydedildi."

    return templates.TemplateResponse(
        request,
        "add_url.html",
        {"categories": list_categories(db_path), "message": message, "error": error},
    )


@router.post("/jobs/scrape-all")
def scrape_all(request: Request, background_tasks: BackgroundTasks) -> RedirectResponse:
    db_path = _db_path(request)
    urls = list_urls(db_path)
    job_id = create_job(db_path, scope="all", total=len(urls))
    background_tasks.add_task(run_scrape_job, db_path=db_path, job_id=job_id)
    return RedirectResponse(url=f"/?job_id={job_id}", status_code=303)


@router.post("/jobs/scrape-category/{category_id}")
def scrape_category(request: Request, category_id: int, background_tasks: BackgroundTasks) -> RedirectResponse:
    db_path = _db_path(request)
    urls = list_urls(db_path, category_id=category_id)
    job_id = create_job(db_path, scope="category", category_id=category_id, total=len(urls))
    background_tasks.add_task(run_scrape_job, db_path=db_path, job_id=job_id, category_id=category_id)
    return RedirectResponse(url=f"/?category_id={category_id}&job_id={job_id}", status_code=303)


@router.post("/import-categories")
def import_categories(request: Request) -> RedirectResponse:
    import_input(settings.categories_dir, _db_path(request))
    return RedirectResponse(url="/", status_code=303)


@router.post("/reset-results")
def reset_results(request: Request) -> RedirectResponse:
    clear_results(_db_path(request))
    return RedirectResponse(url="/", status_code=303)


@router.post("/reset-category/{category_id}")
def reset_category_results(request: Request, category_id: int) -> RedirectResponse:
    clear_results(_db_path(request), category_id=category_id)
    return RedirectResponse(url=f"/?category_id={category_id}", status_code=303)


@router.get("/api/jobs/{job_id}")
def job_status(request: Request, job_id: int) -> JSONResponse:
    row = get_job(_db_path(request), job_id)
    if row is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return JSONResponse(dict(row))
