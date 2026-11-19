from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["catalog_mode"] == "sample"

def test_catalog_search():
    response = client.get("/api/products", params={"q": "laptop"})
    assert response.status_code == 200
    assert len(response.json()) == 4
    assert all(p["data_status"] == "sample" for p in response.json())

def test_missing_product():
    assert client.get("/api/products/999").status_code == 404


def test_sample_detail_exposes_comparison_fields():
    response = client.get("/api/products/1")
    assert response.status_code == 200
    product = response.json()
    assert product["marketplace"] == "Demo catalog"
    assert product["source_url"] is None
    assert product["specifications"] == {"Memory": "16 GB"}


def test_search_returns_empty_results_and_validates_query_length():
    assert client.get("/api/products", params={"q": "unlisted item"}).json() == []
    assert client.get("/api/products", params={"q": "x" * 121}).status_code == 422
