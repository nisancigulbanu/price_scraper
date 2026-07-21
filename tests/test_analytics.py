from price_tracker.analytics import price_stats


def test_price_stats_returns_basic_numeric_analysis():
    rows = [{"price": 10}, {"price": 20}, {"price": 30}, {"price": None}]
    assert price_stats(rows) == {"count": 3, "mean": 20, "median": 20, "min": 10, "max": 30}
