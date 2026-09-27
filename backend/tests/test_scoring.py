"""Unit tests for the honest lead-scoring signal table."""

from __future__ import annotations

import pytest

from backend.scoring import score_company


def _row(**overrides):
    base = {
        "email_valid": None,
        "linkedin": None,
        "phone_normalized": None,
        "quality_score": None,
        "operating_status": None,
        "website": None,
        "employees_min": None,
        "employees_max": None,
        "founded_year": None,
        "industry": None,
    }
    base.update(overrides)
    return base


def test_empty_row_scores_zero():
    score, signals = score_company(_row())
    assert score == 0.0
    assert signals == []


def test_full_signal_row_caps_at_one():
    score, signals = score_company(_row(
        email_valid=True, linkedin="https://linkedin.com/company/x",
        phone_normalized="14155551212", quality_score=0.95,
        operating_status="active", website="https://x.com",
        employees_min=10, employees_max=50, founded_year=2012,
        industry="Software",
    ))
    raw = 0.25 + 0.15 + 0.10 + 0.15 + 0.10 + 0.10 + 0.05 + 0.05 + 0.05
    assert raw == pytest.approx(1.0)
    assert score == 1.0
    assert len(signals) == 9
    assert all(set(s) == {"signal", "points", "detail"} for s in signals)
    assert sum(s["points"] for s in signals) == pytest.approx(raw)


def test_quality_tiers():
    s_hi, _ = score_company(_row(quality_score=0.9))
    s_mid, _ = score_company(_row(quality_score=0.7))
    s_lo, _ = score_company(_row(quality_score=0.69))
    assert s_hi == pytest.approx(0.15)
    assert s_mid == pytest.approx(0.08)
    assert s_lo == 0.0


def test_invalid_email_adds_nothing():
    score, signals = score_company(_row(email_valid=False))
    assert score == 0.0
    assert not [s for s in signals if s["signal"] == "valid_email"]


def test_partial_signals_sum():
    score, signals = score_company(_row(
        email_valid=True, operating_status="active", industry="Software"))
    assert score == pytest.approx(0.25 + 0.10 + 0.05)
    assert {s["signal"] for s in signals} == {"valid_email", "operating_active",
                                             "industry_known"}
