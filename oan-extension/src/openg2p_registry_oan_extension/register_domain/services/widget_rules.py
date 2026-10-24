"""The value rules a section's widgets declare, applied on the server.

The staff UI enforces `widget-data-validation` (pattern, minLength, maxLength,
min, max) in the browser; core does not. The OpenG2P docs place server-side
domain rules in `validate_domain_attributes`, so the domain services apply the
same rules from the same section metadata, and a rule is still written once.

Only rules about a value's form are applied, and only to values that are
present. Whether a field is required depends on the section and on conditions
the UI evaluates, so that stays with the UI and with the domain rules in code.

This module has no database or framework imports, so it can be tested alone.
"""

import logging
import re
from collections.abc import Iterable

_logger = logging.getLogger("oan-widget-rules")

RULE_KEYS = ("pattern", "minLength", "maxLength", "min", "max")

# register id -> field -> rules
Rules = dict[str, dict[str, dict]]


def _widgets(node):
    """Every widget in a section schema, at any depth of panels."""
    if isinstance(node, dict):
        if "widget" in node and ("widget-data-path" in node or "column-key" in node):
            yield node
        for value in node.values():
            yield from _widgets(value)
    elif isinstance(node, list):
        for item in node:
            yield from _widgets(item)


def collect_rules(sections: Iterable[tuple[str, dict]]) -> Rules:
    """Rules per register and field, from (section_register_id, ui_schema) pairs.

    A widget's path is "<register id>.<field>". A table widget's path is
    "<register id>.records", and its columns are fields of that register.
    """
    rules: Rules = {}
    for section_register_id, schema in sections:
        for widget in _widgets(schema or {}):
            path = widget.get("widget-data-path")
            if isinstance(path, str) and "." in path:
                register_id, field = path.split(".", 1)
            elif widget.get("column-key"):
                register_id, field = section_register_id, widget["column-key"]
            else:
                continue
            if field == "records":
                for column in widget.get("widget-data-columns") or []:
                    _add(rules, register_id, column.get("column-key"), column)
            else:
                _add(rules, register_id, field, widget)
    return rules


def _add(rules: Rules, register_id: str, field: str | None, widget: dict) -> None:
    validation = widget.get("widget-data-validation") or {}
    found = {k: validation[k] for k in RULE_KEYS if validation.get(k) is not None}
    if not field or not found:
        return
    if "patternMessage" in validation:
        found["patternMessage"] = validation["patternMessage"]
    existing = rules.setdefault(register_id, {}).setdefault(field, {})
    for key, value in found.items():
        if key in existing and existing[key] != value:
            # Two sections disagree. Keep the first and say so, rather than
            # rejecting what one of the two screens allows.
            _logger.warning("Conflicting %s for %s.%s: %r and %r", key, register_id, field, existing[key], value)
            continue
        existing[key] = value


_compiled: dict[str, re.Pattern | None] = {}


def _regex(pattern: str) -> re.Pattern | None:
    if pattern not in _compiled:
        try:
            _compiled[pattern] = re.compile(pattern)
        except re.error as error:
            # Written for the browser's regex engine and not valid in Python's.
            _logger.warning("Skipping pattern %r: %s", pattern, error)
            _compiled[pattern] = None
    return _compiled[pattern]


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def check_record(record: dict, field_rules: dict[str, dict], messages: dict[str, str] | None = None) -> list[str]:
    """Problems with one record, as "field: message" strings."""
    messages = messages or {}
    problems = []
    for field, rule in field_rules.items():
        value = record.get(field)
        if value is None or value == "":
            continue
        if isinstance(value, str):
            text = value
            if "pattern" in rule:
                regex = _regex(rule["pattern"])
                if regex and not regex.fullmatch(text):
                    key = rule.get("patternMessage")
                    problems.append(f"{field}: {messages.get(key, key) if key else 'has an invalid format'}")
            if "minLength" in rule and len(text) < int(rule["minLength"]):
                problems.append(f"{field}: must be at least {rule['minLength']} characters")
            if "maxLength" in rule and len(text) > int(rule["maxLength"]):
                problems.append(f"{field}: must be at most {rule['maxLength']} characters")
        number = _number(value)
        if number is not None:
            if "min" in rule and number < float(rule["min"]):
                problems.append(f"{field}: must be at least {rule['min']}")
            if "max" in rule and number > float(rule["max"]):
                problems.append(f"{field}: must be at most {rule['max']}")
    return problems
