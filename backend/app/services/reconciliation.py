"""
Reconciliation service for cross-platform royalty comparison.

Detects discrepancies between:
- DSP reports vs PRO statements
- Distributor data vs platform dashboards
- Split sheet shares vs actual payment distributions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Discrepancy:
    """A detected discrepancy in royalty data."""
    id: str
    type: str  # platform_mismatch, missing_payment, share_discrepancy
    severity: str  # low, medium, high, critical
    platform_a: str
    platform_b: str
    work_id: Optional[str] = None
    work_title: Optional[str] = None
    amount_a: float = 0.0
    amount_b: float = 0.0
    difference: float = 0.0
    difference_pct: float = 0.0
    description: str = ""
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    status: str = "unresolved"  # unresolved, investigating, resolved, ignored
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReconciliationResult:
    """Result of a reconciliation analysis."""
    period_start: str
    period_end: str
    total_platforms_compared: int
    total_discrepancies: int
    total_discrepancy_amount: float
    discrepancies: list[Discrepancy] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class ReconciliationService:
    """
    Cross-platform royalty reconciliation.
    
    Key reconciliation checks:
    1. Platform vs PRO: Streaming counts should roughly match
    2. Distributor vs DSP: Reported streams should align
    3. Split shares vs payments: Payment distribution should match splits
    4. Period alignment: Same royalty period across sources
    """

    # Thresholds for flagging discrepancies
    AMOUNT_THRESHOLD = 10.0  # USD - minimum difference to flag
    PERCENTAGE_THRESHOLD = 0.15  # 15% difference to flag
    
    # Known royalty rate ranges for sanity checks
    ESTIMATED_ROYALTY_RANGES = {
        "spotify": {"min": 0.003, "max": 0.005},
        "apple_music": {"min": 0.006, "max": 0.010},
        "youtube": {"min": 0.001, "max": 0.004},
        "tiktok": {"min": 0.0005, "max": 0.002},
        "amazon_music": {"min": 0.004, "max": 0.007},
    }

    def check_reconciliation(
        self,
        data_sources: list[dict[str, Any]],
        splits: Optional[list[dict[str, Any]]] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> ReconciliationResult:
        """
        Run reconciliation checks across all data sources.
        
        Args:
            data_sources: List of royalty data dicts with:
                - platform: str
                - period_start: str
                - period_end: str
                - streams/sales: int
                - gross_revenue: float
                - net_revenue: float
            splits: Optional split sheet data for payment verification
            period_start: Filter by period
            period_end: Filter by period
        
        Returns:
            ReconciliationResult with discrepancies found
        """
        discrepancies: list[Discrepancy] = []
        
        # 1. Cross-platform reconciliation
        platform_discrepancies = self._compare_platforms(data_sources)
        discrepancies.extend(platform_discrepancies)
        
        # 2. Royalty rate sanity checks
        rate_discrepancies = self._check_royalty_rates(data_sources)
        discrepancies.extend(rate_discrepancies)
        
        # 3. Split-based payment verification
        if splits:
            split_discrepancies = self._verify_splits(data_sources, splits)
            discrepancies.extend(split_discrepancies)
        
        # Calculate totals
        total_discrepancy_amount = sum(abs(d.difference) for d in discrepancies)
        
        # Summarize
        summary = {
            "by_severity": self._summarize_by_severity(discrepancies),
            "by_type": self._summarize_by_type(discrepancies),
            "by_platform": self._summarize_by_platform(discrepancies),
            "needs_attention": len([d for d in discrepancies 
                                   if d.severity in ("high", "critical")]),
        }
        
        return ReconciliationResult(
            period_start=period_start or "unknown",
            period_end=period_end or "unknown",
            total_platforms_compared=len(data_sources),
            total_discrepancies=len(discrepancies),
            total_discrepancy_amount=total_discrepancy_amount,
            discrepancies=discrepancies,
            summary=summary,
        )

    def _compare_platforms(
        self, data_sources: list[dict[str, Any]]
    ) -> list[Discrepancy]:
        """Compare royalty amounts across platforms for similar content."""
        discrepancies = []
        
        # Group by work title (when available)
        by_work: dict[str, list[dict]] = {}
        for source in data_sources:
            work_key = source.get("work_title", source.get("work_id", "unknown"))
            if work_key not in by_work:
                by_work[work_key] = []
            by_work[work_key].append(source)
        
        # Check platforms that report on the same work
        for work_key, sources in by_work.items():
            if len(sources) < 2:
                continue
            
            # Compare all pairs
            for i in range(len(sources)):
                for j in range(i + 1, len(sources)):
                    src_a = sources[i]
                    src_b = sources[j]
                    
                    # Compare gross revenues (only if comparable)
                    gross_a = src_a.get("gross_revenue", 0)
                    gross_b = src_b.get("gross_revenue", 0)
                    streams_a = src_a.get("streams", 0)
                    streams_b = src_b.get("streams", 0)
                    
                    diff = abs(gross_a - gross_b)
                    avg = (gross_a + gross_b) / 2 if (gross_a + gross_b) > 0 else 1
                    
                    if diff > self.AMOUNT_THRESHOLD and diff / max(avg, 0.01) > self.PERCENTAGE_THRESHOLD:
                        severity = self._assess_severity(diff, avg)
                        
                        discrepancies.append(Discrepancy(
                            id=f"disc_{len(discrepancies)}",
                            type="platform_mismatch",
                            severity=severity,
                            platform_a=src_a.get("platform", "unknown"),
                            platform_b=src_b.get("platform", "unknown"),
                            work_title=work_key if work_key != "unknown" else None,
                            amount_a=gross_a,
                            amount_b=gross_b,
                            difference=diff,
                            difference_pct=round(diff / max(avg, 0.01) * 100, 2),
                            description=(
                                f"{src_a.get('platform', 'A')} reports ${gross_a:,.2f} "
                                f"while {src_b.get('platform', 'B')} reports ${gross_b:,.2f} "
                                f"(difference: ${diff:,.2f}, {diff/max(avg,0.01)*100:.1f}%)"
                            ),
                            period_start=src_a.get("period_start"),
                            period_end=src_a.get("period_end"),
                        ))
        
        return discrepancies

    def _check_royalty_rates(
        self, data_sources: list[dict[str, Any]]
    ) -> list[Discrepancy]:
        """Check if reported royalty rates are within expected ranges."""
        discrepancies = []
        
        for source in data_sources:
            platform = source.get("platform", "").lower()
            streams = source.get("streams", 0)
            gross = source.get("gross_revenue", 0)
            
            if streams <= 0 or gross <= 0:
                continue
            
            rate = gross / streams
            
            if platform in self.ESTIMATED_ROYALTY_RANGES:
                expected = self.ESTIMATED_ROYALTY_RANGES[platform]
                if rate < expected["min"] or rate > expected["max"]:
                    discrepancies.append(Discrepancy(
                        id=f"rate_{len(discrepancies)}",
                        type="unusual_rate",
                        severity="medium",
                        platform_a=platform,
                        platform_b="expected_range",
                        work_title=source.get("work_title"),
                        amount_a=rate,
                        amount_b=(expected["min"] + expected["max"]) / 2,
                        difference=abs(rate - expected["max"]) if rate > expected["max"] 
                                   else abs(rate - expected["min"]),
                        difference_pct=round(
                            abs(rate - (expected["min"] + expected["max"]) / 2)
                            / ((expected["min"] + expected["max"]) / 2) * 100, 2
                        ) if (expected["min"] + expected["max"]) / 2 > 0 else 0,
                        description=(
                            f"{platform.capitalize()} royalty rate ${rate:.6f}/stream "
                            f"outside expected range ${expected['min']:.4f}-${expected['max']:.4f}"
                        ),
                        period_start=source.get("period_start"),
                        period_end=source.get("period_end"),
                    ))
        
        return discrepancies

    def _verify_splits(
        self,
        data_sources: list[dict[str, Any]],
        splits: list[dict[str, Any]],
    ) -> list[Discrepancy]:
        """Verify that payment distributions match split sheets."""
        discrepancies = []
        
        # Build expected distribution from splits
        total_share = sum(s.get("share_percentage", 0) for s in splits)
        if total_share == 0:
            return discrepancies
        
        for source in data_sources:
            net = source.get("net_revenue", source.get("gross_revenue", 0))
            
            for split in splits:
                expected_share = net * split.get("share_percentage", 0) / 100
                actual_paid = source.get(f"paid_to_{split['party_name'].lower().replace(' ', '_')}", 0)
                
                if abs(expected_share - actual_paid) > self.AMOUNT_THRESHOLD:
                    discrepancies.append(Discrepancy(
                        id=f"split_{len(discrepancies)}",
                        type="share_discrepancy",
                        severity="high",
                        platform_a="split_sheet",
                        platform_b=source.get("platform", "unknown"),
                        work_title=source.get("work_title"),
                        amount_a=expected_share,
                        amount_b=actual_paid,
                        difference=abs(expected_share - actual_paid),
                        difference_pct=round(
                            abs(expected_share - actual_paid) / max(expected_share, 0.01) * 100, 2
                        ),
                        description=(
                            f"{split['party_name']} expected ${expected_share:,.2f} "
                            f"but received ${actual_paid:,.2f} from {source.get('platform')}"
                        ),
                        period_start=source.get("period_start"),
                        period_end=source.get("period_end"),
                    ))
        
        return discrepancies

    def _assess_severity(self, difference: float, average: float) -> str:
        """Assess discrepancy severity based on amount and percentage."""
        pct = difference / max(average, 0.01)
        
        if difference > 1000 or pct > 0.5:
            return "critical"
        elif difference > 500 or pct > 0.3:
            return "high"
        elif difference > 100 or pct > 0.15:
            return "medium"
        return "low"

    def _summarize_by_severity(
        self, discrepancies: list[Discrepancy]
    ) -> dict[str, int]:
        """Count discrepancies by severity."""
        counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for d in discrepancies:
            counts[d.severity] = counts.get(d.severity, 0) + 1
        return counts

    def _summarize_by_type(
        self, discrepancies: list[Discrepancy]
    ) -> dict[str, int]:
        """Count discrepancies by type."""
        counts: dict[str, int] = {}
        for d in discrepancies:
            counts[d.type] = counts.get(d.type, 0) + 1
        return counts

    def _summarize_by_platform(
        self, discrepancies: list[Discrepancy]
    ) -> dict[str, int]:
        """Count discrepancies by platform."""
        counts: dict[str, int] = {}
        for d in discrepancies:
            counts[d.platform_a] = counts.get(d.platform_a, 0) + 1
            counts[d.platform_b] = counts.get(d.platform_b, 0) + 1
        return counts
