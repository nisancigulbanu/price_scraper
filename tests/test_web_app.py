from fastapi.testclient import TestClient

from price_tracker.web.app import create_app


def test_dashboard_renders_and_add_url_flow_works(tmp_path):
    app = create_app(tmp_path / "web.sqlite3")
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Price Tracker" in response.text

        add_response = client.post(
            "/add-url",
            data={
                "category_mode": "new",
                "new_category": "test_kategori",
                "urls": "https://example.com/product",
            },
        )
        assert add_response.status_code == 200
        assert "1 yeni URL kaydedildi" in add_response.text
