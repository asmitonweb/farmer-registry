"""Values the registry derives from what was entered, never typed in.

The domain services apply these on every way in: the intake form and change
requests (validate_domain_attributes, pre_approve) and ingestion (post_ingest).
The previous farmer registry computed the same values with SQL backfills at
startup; here they are kept in step as records are saved.

This module has no database or framework imports, so it can be tested alone.
"""

from collections.abc import Iterable
from datetime import date, datetime

from .ethiopian_calendar import (
    ethiopic_to_gregorian,
    format_ethiopic,
    gregorian_to_ethiopic_string,
    parse_ethiopic,
)

UNIT_TO_HECTARES = {
    "HECTARE": 1.0,
    "ACRE": 0.404686,
    "SQUARE_METER": 0.0001,
    "SQUARE_KM": 100.0,
    "SQUARE_FOOT": 0.0000092903,
    "SQUARE_YARD": 0.0000836127,
}

# geo_code_hierarchy_json level -> farmer column holding that level's name
GEO_NAME_FIELDS = {"region": "region_name", "zone": "zone_name", "woreda": "woreda_name", "kebele": "kebele_name"}


class DerivationError(ValueError):
    """An entered value the derivation cannot use; the message is for the user."""


def _number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).strip()).date()
    except ValueError:
        return None


def hectares(size, unit) -> float | None:
    """A land size in hectares; an unknown unit counts as hectares, as before."""
    size = _number(size)
    if size is None:
        return None
    return round(size * UNIT_TO_HECTARES.get(str(unit or "HECTARE"), 1.0), 6)


def land_rollup(lands: Iterable[tuple[str | None, float | None]]) -> dict:
    """A farmer's land totals from (ownership type, hectares) per active parcel.

    Owned is OWNER, rented is TENANT, and crop sharing is every other parcel.
    The farmer's land ownership is OWNER or TENANT when every typed parcel is
    that, HYBRID when they differ, and empty when no parcel has a type.
    """
    owned = rented = shared = total = 0.0
    kinds: set[str] = set()
    for kind, area in lands:
        area = area or 0.0
        total += area
        if kind == "OWNER":
            owned += area
        elif kind == "TENANT":
            rented += area
        else:
            shared += area
        if kind:
            kinds.add(kind)
    if not kinds:
        ownership = None
    elif len(kinds) == 1 and next(iter(kinds)) in ("OWNER", "TENANT"):
        ownership = next(iter(kinds))
    else:
        ownership = "HYBRID"
    return {
        "total_land_area": round(total, 6),
        "total_land_owned_area": round(owned, 6),
        "total_land_rent_area": round(rented, 6),
        "total_land_crop_sharing_area": round(shared, 6),
        "land_ownership": ownership,
    }


def geo_names(hierarchy) -> dict:
    """region_name .. kebele_name from the geo widget's hierarchy value."""
    levels = (hierarchy or {}).get("hierarchy") if isinstance(hierarchy, dict) else None
    names = dict.fromkeys(GEO_NAME_FIELDS.values())
    for level in levels or []:
        field = GEO_NAME_FIELDS.get(str(level.get("level_mnemonic") or "").lower())
        if field:
            names[field] = level.get("level_value_mnemonic") or None
    return names


def sync_ethiopic(record: dict, gc_field: str, ec_field: str) -> None:
    """Keep a Gregorian date and its Ethiopian calendar twin in step.

    The Gregorian date is the one stored and compared (the OpenG2P approach to
    the Ethiopian calendar); the Ethiopian one is derived from it. Only when no
    Gregorian date was given is it taken from the Ethiopian one. A record that
    carries neither field is left alone, so a partial update derives nothing.
    """
    if gc_field not in record and ec_field not in record:
        return
    gregorian = _date(record.get(gc_field))
    if gregorian is not None:
        record[ec_field] = gregorian_to_ethiopic_string(gregorian)
        return
    raw = record.get(ec_field)
    if raw in (None, ""):
        for field in (gc_field, ec_field):
            if field in record:
                record[field] = None
        return
    ethiopic = parse_ethiopic(raw)
    if ethiopic is None:
        raise DerivationError(f"{ec_field} must be an Ethiopian date written as YYYY-MM-DD")
    try:
        record[gc_field] = ethiopic_to_gregorian(*ethiopic).isoformat()
    except ValueError:
        raise DerivationError(
            f"{ec_field} {format_ethiopic(*ethiopic)} is not an Ethiopian date "
            "(months 1-12 have 30 days, Pagumen 5 or 6)"
        ) from None
    record[ec_field] = format_ethiopic(*ethiopic)


def ethiopic_of(value) -> str | None:
    gregorian = _date(value)
    return gregorian_to_ethiopic_string(gregorian) if gregorian else None


# Ethiopian numbers: 9 national digits, mobile 9xx or 7xx, landline area codes.
ETHIOPIA_CALLING_CODE = "251"


def normalize_phone(number, country_code=None) -> tuple[str | None, str | None]:
    """(national number, E.164) for a phone number as typed.

    For Ethiopia (the default) +251 912 345 678, 0912345678 and 912345678 are
    one number, stored as its 9 national digits. Any other country's number is
    kept as typed, without spaces. A number that cannot be read returns
    (None, None).
    """
    raw = "".join(ch for ch in str(number or "") if ch.isdigit() or ch == "+")
    if not raw:
        return None, None
    country = str(country_code or "ET").upper()
    if country not in ("ET", "ETH"):
        return raw, raw if raw.startswith("+") else None
    digits = raw.lstrip("+")
    digits = digits.removeprefix(ETHIOPIA_CALLING_CODE)
    digits = digits.removeprefix("0")
    if len(digits) != 9 or not digits.isdigit():
        return None, None
    return digits, f"+{ETHIOPIA_CALLING_CODE}{digits}"


# What a user types to find a farmer: the ids, and the names in each language
# (the middle name is the father's). search_text is indexed and matched as one
# string, so anything else (gender, education, dates, coordinates) is left to
# the list filters, as OpenG2P advises.
FARMER_SEARCH_FIELDS = (
    "functional_record_id", "foundational_id", "rid",
    "first_name", "middle_name", "last_name",
    "first_name_amh", "middle_name_amh", "last_name_amh",
    "first_name_other", "middle_name_other", "last_name_other",
)


def farmer_search_text(payload: dict, extra=None) -> str:
    values = [*(extra or []), *(payload.get(field) for field in FARMER_SEARCH_FIELDS)]
    return " ".join(dict.fromkeys(str(v).strip() for v in values if v is not None and str(v).strip()))
