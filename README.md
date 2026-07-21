# Price Tracker

Local web application for importing category URL lists, scraping product prices, and reviewing price statistics.

## Run

```bash
pip install -r requirements.txt
python -m price_tracker.main --import-categories
python -m price_tracker.main --serve
```

Playwright fallback is optional. Install it separately only if JavaScript-rendered product pages need browser fetching.

Open `http://127.0.0.1:8000`.

## Useful Commands

```bash
python -m price_tracker.main --input kategoriler --limit 20 --output data/output/prices.xlsx
python -m price_tracker.main --serve --host 127.0.0.1 --port 8000
pytest
```
