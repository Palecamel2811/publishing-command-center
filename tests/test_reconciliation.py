import pytest
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.reconciliation import ReconciliationService


def test_reconciliation_service_initialization():
    service = ReconciliationService()
    assert service.AMOUNT_THRESHOLD == 10.0
    assert service.PERCENTAGE_THRESHOLD == 0.15


def test_reconciliation_platform_mismatch():
    service = ReconciliationService()
    data_sources = [
        {
            "work_title": "Golden Hour",
            "platform": "spotify",
            "gross_revenue": 10000.0,
            "net_revenue": 8500.0,
            "streams": 2500000,
        },
        {
            "work_title": "Golden Hour",
            "platform": "apple_music",
            "gross_revenue": 5000.0,
            "net_revenue": 4250.0,
            "streams": 700000,
        },
    ]
    result = service.check_reconciliation(data_sources=data_sources)
    assert result.total_platforms_compared == 2
    assert len(result.discrepancies) >= 1
    mismatch = [d for d in result.discrepancies if d.type == "platform_mismatch"]
    assert len(mismatch) == 1
    assert mismatch[0].difference == 5000.0


def test_reconciliation_split_verification():
    service = ReconciliationService()
    data_sources = [
        {
            "work_title": "Golden Hour",
            "platform": "spotify",
            "gross_revenue": 10000.0,
            "net_revenue": 10000.0,
            "paid_to_jordan_lee": 4000.0,  # Expected 6000.0 (60%)
            "paid_to_you": 4000.0,
        }
    ]
    splits = [
        {"party_name": "Jordan Lee", "share_percentage": 60.0},
        {"party_name": "You", "share_percentage": 40.0},
    ]
    result = service.check_reconciliation(data_sources=data_sources, splits=splits)
    split_disc = [d for d in result.discrepancies if d.type == "share_discrepancy"]
    assert len(split_disc) >= 1
    assert any("Jordan Lee" in d.description for d in split_disc)
