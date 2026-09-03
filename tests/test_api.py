import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_dashboard_endpoint(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "works" in data
    assert "sync_licenses" in data
    assert "reconciliation_status" in data
    assert "revenue_trend" in data
    assert len(data["works"]) >= 1


def test_works_endpoints(client):
    response = client.get("/api/works")
    assert response.status_code == 200
    data = response.json()
    assert "works" in data
    assert data["count"] >= 1


def test_sync_licenses_endpoints(client):
    response = client.get("/api/sync-licenses")
    assert response.status_code == 200
    data = response.json()
    assert "sync_licenses" in data
    assert data["count"] >= 1


def test_royalties_endpoint(client):
    response = client.get("/api/dashboard/royalties")
    assert response.status_code == 200
    data = response.json()
    assert "royalties" in data
    assert "summary" in data
    assert len(data["royalties"]) >= 1


def test_reports_csv_export(client):
    response = client.get("/api/reports/export?report_type=royalties")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "Work,Platform,Royalty Type" in response.text


def test_reports_csv_export_invalid_type(client):
    response = client.get("/api/reports/export?report_type=invalid_type")
    assert response.status_code == 400 or response.status_code == 422


@pytest.mark.parametrize("query_text", [
    "How much did I earn from Spotify for Golden Hour?",
    "What are the split terms for Sauce?",
    "Show me sync license terms for film placements",
    "What is the capital of France?",  # Out-of-domain query test
])
def test_query_endpoint_unbiased(client, query_text):
    response = client.post("/api/query", json={"query": query_text})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "sources" in data
    assert "confidence" in data
    assert isinstance(data["response"], str)
    assert isinstance(data["sources"], list)
    assert isinstance(data["confidence"], (int, float))
    assert 0.0 <= data["confidence"] <= 1.0


def test_query_endpoint_empty_query(client):
    response = client.post("/api/query", json={"query": ""})
    assert response.status_code in [200, 400, 422]

