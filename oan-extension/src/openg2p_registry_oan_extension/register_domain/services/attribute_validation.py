"""Validate metadata-backed choices with the platform Master Data transport.

The fetched catalog is local to this validation request/batch. No process cache
or fallback permits a submitted value when the authoritative list is unavailable.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def _blank(value):
    return value is None or isinstance(value, str) and not value.strip()


async def check_attribute_values(records, field_rules, say, post):
    pending = [
        (field, rule, record[field])
        for record in records
        for field, rule in field_rules.items()
        if rule.get("master_data") and field in record and not _blank(record[field])
    ]
    if not pending:
        return []
    labels = {field: say.label(rule.get("label"), field) for field, rule, _ in pending}
    catalog = {}
    try:
        if post is None:
            raise RuntimeError("Master Data client is not registered")
        # Only lists referenced by submitted nonblank fields are fetched. All
        # fields/rows using the same list share its pages within this batch.
        attributes = dict.fromkeys(
            rule["master_data"]["attribute_id"] for _, rule, _ in pending
        )
        for attribute in attributes:
            choices = catalog.setdefault(attribute, {})
            for page in range(1, 201):
                payload = await post(
                    "/attributes/get_attribute_values",
                    payload={"attribute_id": attribute},
                    pagination={"current_page": page, "page_size": 1000},
                )
                rows = (
                    payload.get("attribute_values")
                    if isinstance(payload, dict)
                    else payload
                )
                if not isinstance(rows, list):
                    raise TypeError("Invalid Master Data response")
                for row in rows:
                    if not isinstance(row, dict) or not row.get("attribute_id"):
                        raise ValueError("Invalid Master Data attribute row")
                    if row["attribute_id"] != attribute:
                        continue
                    for key in ("value_code", "value_id"):
                        value = row.get(key)
                        if value is not None and not isinstance(
                            value, (dict, list, bool)
                        ):
                            choices.setdefault(key, set()).add(str(value))
                if len(rows) < 1000:
                    break
                if (
                    isinstance(payload, dict)
                    and isinstance(payload.get("total"), int)
                    and page * 1000 >= payload["total"]
                ):
                    break
            else:
                raise ValueError("Master Data pagination limit exceeded")
    except Exception:  # noqa: BLE001 -- native transport errors must fail closed without leaking credentials
        # Never expose transport details or credentials in a field error.
        return [
            say("oan_rule_mds_unavailable", label=label)
            for label in dict.fromkeys(labels.values())
        ]

    problems = []
    for field, rule, value in pending:
        binding = rule["master_data"]
        choices = catalog.get(binding["attribute_id"], {}).get(binding["value_key"])
        if not choices:
            problems.append(say("oan_rule_mds_unavailable", label=labels[field]))
        elif isinstance(value, (dict, list, bool)) or str(value) not in choices:
            problems.append(say("oan_rule_option", label=labels[field], value=value))
    return problems


def check_domain_bounds(records, mnemonic, field_rules, say, today=None):
    today = today or date.today()
    field = (
        "year_of_acquisition"
        if mnemonic == "Land"
        else "collected_date"
        if mnemonic == "Livestock"
        else None
    )
    if field is None:
        return []
    label = say.label(field_rules.get(field, {}).get("label"), field)
    problems = []
    for record in records:
        value = record.get(field)
        if _blank(value):
            continue
        if mnemonic == "Land":
            try:
                number = Decimal(str(value))
                year = (
                    int(number)
                    if number.is_finite() and number == number.to_integral_value()
                    else None
                )
            except (InvalidOperation, ValueError, TypeError):
                year = None
            if year is None or not 1900 <= year <= today.year:
                problems.append(
                    say("oan_rule_year_range", label=label, year=today.year)
                )
        else:
            if isinstance(value, datetime):
                parsed = value.date()
            elif isinstance(value, date):
                parsed = value
            else:
                try:
                    parsed = date.fromisoformat(str(value))
                except ValueError:
                    parsed = None
            if parsed is None:
                problems.append(say("oan_rule_date", label=label, value=value))
            elif parsed > today:
                problems.append(say("oan_rule_future_date", label=label))
    return problems
