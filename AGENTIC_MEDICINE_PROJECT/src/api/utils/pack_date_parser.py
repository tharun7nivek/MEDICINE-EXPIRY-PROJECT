"""
pack_date_parser.py
-------------------
Deterministic pharmaceutical pack-date parsing.

Handles the many printed formats found on medicine packs (dots, spaces,
slashes, dashes, month abbreviations, day-precision and month-precision).
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Match, Optional

DatePrecision = Literal["day", "month"]

MONTH_ABBR: dict[str, int] = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "SEPT": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

MONTH_FULL: dict[str, int] = {
    "JANUARY": 1,
    "FEBRUARY": 2,
    "MARCH": 3,
    "APRIL": 4,
    "MAY": 5,
    "JUNE": 6,
    "JULY": 7,
    "AUGUST": 8,
    "SEPTEMBER": 9,
    "OCTOBER": 10,
    "NOVEMBER": 11,
    "DECEMBER": 12,
}

_MONTH_TOKEN = (
    r"(?P<mon>"
    + "|".join(
        sorted(
            {**MONTH_ABBR, **MONTH_FULL}.keys(),
            key=len,
            reverse=True,
        )
    )
    + r")"
)


@dataclass(frozen=True)
class ParsedPackDate:
    """Parsed pack date with calendar precision."""

    year: int
    month: int
    day: int
    precision: DatePrecision

    @property
    def as_date(self) -> date:
        return date(self.year, self.month, self.day)

    def valid_through(self) -> date:
        """
        Last calendar day the medicine is considered valid.

        Month-only pack dates (e.g. MAR.2027) remain valid through month end.
        """
        if self.precision == "day":
            return self.as_date
        last_day = calendar.monthrange(self.year, self.month)[1]
        return date(self.year, self.month, last_day)

    def to_datetime(self) -> datetime:
        """First moment of the printed period (compat with older validate_node)."""
        return datetime(self.year, self.month, self.day)


def normalize_pack_date(raw: str) -> str:
    """Uppercase, collapse whitespace, tidy repeated separators."""
    value = raw.strip().upper()
    value = re.sub(r"\s+", " ", value)
    value = value.replace("--", "-")
    # Drop trailing punctuation often left by OCR ("MAR.2027.")
    value = value.strip(" .")
    return value


def _month_number(token: str) -> Optional[int]:
    token = token.upper()
    return MONTH_ABBR.get(token) or MONTH_FULL.get(token)


def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    if month < 1 or month > 12:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_pack_date(raw: str | None) -> Optional[ParsedPackDate]:
    """
    Parse a medicine-pack date string into year/month(/day).

    Returns None when *raw* is empty or does not match a known format.
    """
    if raw is None:
        return None
    text = normalize_pack_date(raw)
    if not text:
        return None

    compact = re.sub(r"[\s]", "", text)

    patterns: list[
        tuple[str, DatePrecision, Callable[[Match[str]], Optional[date]]]
    ] = [
        # YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD
        (
            r"^(?P<y>\d{4})[-/.](?P<m>0[1-9]|1[0-2])[-/.](?P<d>0[1-9]|[12]\d|3[01])$",
            "day",
            lambda m: _safe_date(int(m["y"]), int(m["m"]), int(m["d"])),
        ),
        # DD-MM-YYYY / DD/MM/YYYY / DD.MM.YYYY
        (
            r"^(?P<d>0[1-9]|[12]\d|3[01])[-/.](?P<m>0[1-9]|1[0-2])[-/.](?P<y>\d{4})$",
            "day",
            lambda m: _safe_date(int(m["y"]), int(m["m"]), int(m["d"])),
        ),
        # DD MMM YYYY / DD-MMM-YYYY / DD.MMM.YYYY / DD/MMM/YYYY
        (
            rf"^(?P<d>0?[1-9]|[12]\d|3[01])[.\-/\s]+{_MONTH_TOKEN}[.\-/\s]+(?P<y>\d{{4}})$",
            "day",
            lambda m: _safe_date(
                int(m["y"]), _month_number(m["mon"]) or 0, int(m["d"])
            ),
        ),
        # MMM DD, YYYY / MMM DD YYYY / MMM-DD-YYYY
        (
            rf"^{_MONTH_TOKEN}[.\-/\s]+(?P<d>0?[1-9]|[12]\d|3[01]),?[.\-/\s]+(?P<y>\d{{4}})$",
            "day",
            lambda m: _safe_date(
                int(m["y"]), _month_number(m["mon"]) or 0, int(m["d"])
            ),
        ),
        # YYYY-MM / YYYY/MM / YYYY.MM
        (
            r"^(?P<y>\d{4})[-/.](?P<m>0[1-9]|1[0-2])$",
            "month",
            lambda m: _safe_date(int(m["y"]), int(m["m"]), 1),
        ),
        # MM/YYYY / MM-YYYY / MM.YYYY
        (
            r"^(?P<m>0[1-9]|1[0-2])[-/.](?P<y>\d{4})$",
            "month",
            lambda m: _safe_date(int(m["y"]), int(m["m"]), 1),
        ),
        # MMMYYYY / MMM.YYYY / MMM-YYYY / MMM/YYYY / MMM YYYY (+ full names)
        (
            rf"^{_MONTH_TOKEN}[.\-/]?(?P<y>\d{{4}})$",
            "month",
            lambda m: _safe_date(int(m["y"]), _month_number(m["mon"]) or 0, 1),
        ),
        # YYYYMMDD (20240815) — before YYYYMM
        (
            r"^(?P<y>\d{4})(?P<m>0[1-9]|1[0-2])(?P<d>0[1-9]|[12]\d|3[01])$",
            "day",
            lambda m: _safe_date(int(m["y"]), int(m["m"]), int(m["d"])),
        ),
        # YYYYMM (202408)
        (
            r"^(?P<y>\d{4})(?P<m>0[1-9]|1[0-2])$",
            "month",
            lambda m: _safe_date(int(m["y"]), int(m["m"]), 1),
        ),
        # DDMMYYYY (15082024)
        (
            r"^(?P<d>0[1-9]|[12]\d|3[01])(?P<m>0[1-9]|1[0-2])(?P<y>\d{4})$",
            "day",
            lambda m: _safe_date(int(m["y"]), int(m["m"]), int(m["d"])),
        ),
    ]

    candidates = (text, compact) if text != compact else (text,)
    for candidate in candidates:
        for regex, precision, builder in patterns:
            match = re.fullmatch(regex, candidate, flags=re.IGNORECASE)
            if not match:
                continue
            parsed_day = builder(match)
            if parsed_day is None:
                continue
            return ParsedPackDate(
                year=parsed_day.year,
                month=parsed_day.month,
                day=parsed_day.day if precision == "day" else 1,
                precision=precision,
            )

    return None


def is_expired(parsed: ParsedPackDate, *, today: date | None = None) -> bool:
    """True when *today* is after the last valid day for *parsed*."""
    ref = today or date.today()
    return ref > parsed.valid_through()


def parse_date(raw: str | None) -> Optional[datetime]:
    """
    Back-compat helper matching validate_node's historic return type.

    Returns datetime at day 1 for month-precision dates.
    """
    parsed = parse_pack_date(raw)
    if parsed is None:
        return None
    return parsed.to_datetime()
