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


def test_query_endpoint(client):
    response = client.post("/api/query", json={"query": "How much did I earn from Spotify for Golden Hour?"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "sources" in data
    assert "confidence" in data
    assert len(data["sources"]) >= 1
