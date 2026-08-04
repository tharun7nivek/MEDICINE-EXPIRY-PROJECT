"""Unit tests for pack date parsing + expiry assessment."""

from __future__ import annotations

from datetime import date

import pytest

from src.api.core.services.expiry_assessment_service import ExpiryAssessmentService
from src.api.utils.pack_date_parser import parse_pack_date


@pytest.mark.parametrize(
    "raw, year, month, day, precision",
    [
        ("2024-08", 2024, 8, 1, "month"),
        ("2024/08", 2024, 8, 1, "month"),
        ("08/2024", 2024, 8, 1, "month"),
        ("08-2024", 2024, 8, 1, "month"),
        ("08.2024", 2024, 8, 1, "month"),
        ("AUG2024", 2024, 8, 1, "month"),
        ("APR.2024", 2024, 4, 1, "month"),
        ("MAR.2027", 2027, 3, 1, "month"),
        ("MAR. 2027", 2027, 3, 1, "month"),
        ("MARCH 2027", 2027, 3, 1, "month"),
        ("202408", 2024, 8, 1, "month"),
        ("15-08-2024", 2024, 8, 15, "day"),
        ("15/08/2024", 2024, 8, 15, "day"),
        ("15.08.2024", 2024, 8, 15, "day"),
        ("2024-08-15", 2024, 8, 15, "day"),
        ("15 AUG 2024", 2024, 8, 15, "day"),
        ("15-AUG-2024", 2024, 8, 15, "day"),
        ("AUG 15, 2024", 2024, 8, 15, "day"),
        ("20240815", 2024, 8, 15, "day"),
        ("15082024", 2024, 8, 15, "day"),
    ],
)
def test_parse_pack_date_formats(raw, year, month, day, precision):
    parsed = parse_pack_date(raw)
    assert parsed is not None
    assert parsed.year == year
    assert parsed.month == month
    assert parsed.day == day
    assert parsed.precision == precision


def test_parse_pack_date_rejects_garbage():
    assert parse_pack_date("not-a-date") is None
    assert parse_pack_date(None) is None
    assert parse_pack_date("") is None


def test_assessment_not_expired_for_future_month():
    svc = ExpiryAssessmentService()
    result = svc.assess(
        "APR.2024",
        "MAR.2027",
        status="human_review",
        today=date(2026, 8, 3),
    )
    assert result.expiry_status == "valid"
    assert result.is_expired is False
    assert result.exp_parsed is True
    assert result.exp_valid_through == "2027-03-31"
    # pipeline flagged review
    assert result.needs_human_review is True


def test_assessment_expired_past_month():
    svc = ExpiryAssessmentService()
    result = svc.assess(
        "JAN.2020",
        "APR.2024",
        status="accepted",
        today=date(2026, 8, 3),
    )
    assert result.expiry_status == "expired"
    assert result.is_expired is True
    assert result.needs_human_review is False


def test_assessment_unknown_when_unparsed():
    svc = ExpiryAssessmentService()
    result = svc.assess(None, "N/A", status="accepted", today=date(2026, 8, 3))
    assert result.expiry_status == "unknown"
    assert result.is_expired is None
    assert result.needs_human_review is True
