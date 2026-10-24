"""Tests for the server-side widget rules.

widget_rules.py has no framework imports, so it is loaded by path and these
tests run without the registry installed:

    uv run --no-project --with pytest pytest oan-extension/tests
"""

import importlib.util
from pathlib import Path

_PATH = Path(__file__).parents[1] / "src/openg2p_registry_oan_extension/register_domain/services/widget_rules.py"
_spec = importlib.util.spec_from_file_location("widget_rules", _PATH)
widget_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(widget_rules)

FARMER = "a1a4d25a-1cd4-4356-abac-985a0b3c6bcd"
LAND = "493153d5-07ef-4743-8efd-07f4099772b9"
ETHIOPIC = "^[\\u1200-\\u137F\\u2D80-\\u2DDF\\uAB00-\\uAB2F ]+$"

PERSONAL = {"panels": [{"panels": [{"widgets": [
    {"widget": "text", "widget-id": "first_name_amh", "widget-data-path": f"{FARMER}.first_name_amh",
     "widget-data-validation": {"pattern": ETHIOPIC, "maxLength": 10, "patternMessage": "ethiopic_script_only"}},
    {"widget": "number", "widget-id": "estimated_age", "widget-data-path": f"{FARMER}.estimated_age",
     "widget-data-validation": {"min": 0, "max": 122}},
    {"widget": "text", "widget-id": "middle_name", "widget-data-path": f"{FARMER}.middle_name"},
]}]}]}

LANDS = {"panels": [{"panels": [{"widgets": [
    {"widget": "table", "widget-id": "lands_table", "widget-data-path": f"{LAND}.records", "widget-data-columns": [
        {"widget": "number", "column-key": "land_size", "widget-data-path": "land_size",
         "widget-data-validation": {"min": 0.01, "minMessage": "land_size_positive"}},
        {"widget": "text", "column-key": "land_id", "widget-data-path": "land_id",
         "widget-data-validation": {"maxLength": 5}},
    ]},
]}]}]}

RULES = widget_rules.collect_rules([(FARMER, PERSONAL), (LAND, LANDS)])
MESSAGES = {"ethiopic_script_only": "Use Ethiopic (Ge'ez) script"}


def test_collects_widget_and_table_column_rules():
    assert set(RULES) == {FARMER, LAND}
    assert set(RULES[FARMER]) == {"first_name_amh", "estimated_age"}
    assert RULES[LAND]["land_size"] == {"min": 0.01}
    assert RULES[LAND]["land_id"] == {"maxLength": 5}


def test_widget_without_rules_is_not_listed():
    assert "middle_name" not in RULES[FARMER]


def test_valid_values_pass():
    record = {"first_name_amh": "አበበ", "estimated_age": 40}
    assert widget_rules.check_record(record, RULES[FARMER], MESSAGES) == []


def test_pattern_uses_the_translated_message():
    problems = widget_rules.check_record({"first_name_amh": "Abebe"}, RULES[FARMER], MESSAGES)
    assert problems == ["first_name_amh: Use Ethiopic (Ge'ez) script"]


def test_pattern_message_key_is_used_when_untranslated():
    problems = widget_rules.check_record({"first_name_amh": "Abebe"}, RULES[FARMER], {})
    assert problems == ["first_name_amh: ethiopic_script_only"]


def test_length_and_range():
    problems = widget_rules.check_record({"first_name_amh": "አበበአበበአበበአበ", "estimated_age": 130}, RULES[FARMER])
    assert problems == ["first_name_amh: must be at most 10 characters", "estimated_age: must be at most 122"]


def test_numbers_sent_as_text_are_checked():
    assert widget_rules.check_record({"land_size": "0"}, RULES[LAND]) == ["land_size: must be at least 0.01"]


def test_empty_values_are_left_to_the_required_rules():
    record = {"first_name_amh": "", "estimated_age": None}
    assert widget_rules.check_record(record, RULES[FARMER]) == []


def test_booleans_are_not_numbers():
    assert widget_rules.check_record({"estimated_age": True}, RULES[FARMER]) == []


def test_conflicting_sections_keep_the_first_rule():
    other = {"panels": [{"widgets": [{"widget": "number", "widget-data-path": f"{FARMER}.estimated_age",
                                      "widget-data-validation": {"max": 100}}]}]}
    rules = widget_rules.collect_rules([(FARMER, PERSONAL), (FARMER, other)])
    assert rules[FARMER]["estimated_age"]["max"] == 122


def test_a_pattern_python_cannot_compile_is_skipped():
    rules = {"code": {"pattern": "(?<name"}}
    assert widget_rules.check_record({"code": "x"}, rules) == []
