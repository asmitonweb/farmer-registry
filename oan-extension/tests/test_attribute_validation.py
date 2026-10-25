"""Metadata-bound MDS choices and date/year domain boundaries."""

import asyncio
import importlib.util
from datetime import date
from pathlib import Path

import pytest

SERVICES = (
    Path(__file__).parents[1]
    / "src/openg2p_registry_oan_extension/register_domain/services"
)


def load(name):
    spec = importlib.util.spec_from_file_location(name, SERVICES / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validation = load("attribute_validation")
widgets = load("widget_rules")
say = widgets._Say(
    {
        "gender": "Gender",
        "breed": "Breed",
        "year_of_acquisition": "Year of Acquisition",
        "collected_date": "Count Date",
    }
)


def rules(value_key="value_code", field="gender", attribute="GENDER"):
    return widgets.collect_rules(
        [
            (
                "farmer",
                {
                    "widgets": [
                        {
                            "widget": "select",
                            "widget-id": field,
                            "widget-data-path": "farmer." + field,
                            "widget-data-source": {
                                "type": "api",
                                "service": "attributes",
                                "endpoint": "values",
                                "params": {"attribute_id": attribute},
                                "valueKey": value_key,
                            },
                        }
                    ]
                },
            )
        ]
    )["farmer"]


def test_code_choices_share_one_catalog_for_all_rows():
    calls = []

    async def post(path, **kwargs):
        calls.append((path, kwargs))
        return [{"attribute_id": "GENDER", "value_code": "MALE", "value_id": 10}]

    assert (
        asyncio.run(
            validation.check_attribute_values(
                [{"gender": "MALE"}] * 4, rules(), say, post
            )
        )
        == []
    )
    assert len(calls) == 1
    assert calls[0][0] == "/attributes/get_attribute_values"
    assert calls[0][1]["payload"] == {"attribute_id": "GENDER"}
    assert asyncio.run(
        validation.check_attribute_values([{"gender": "male"}], rules(), say, post)
    ) == ['Gender: "male" is not one of the choices. Pick one from the list.']


def test_id_bound_field_accepts_id_and_refuses_code():
    async def post(*args, **kwargs):
        return [
            {"attribute_id": "LIVESTOCK_BREED", "value_code": "LOCAL", "value_id": 42}
        ]

    rule = rules("value_id", "breed", "LIVESTOCK_BREED")
    assert (
        asyncio.run(
            validation.check_attribute_values(
                [{"breed": 42}, {"breed": "42"}], rule, say, post
            )
        )
        == []
    )
    assert asyncio.run(
        validation.check_attribute_values([{"breed": "LOCAL"}], rule, say, post)
    ) == ['Breed: "LOCAL" is not one of the choices. Pick one from the list.']


def test_fetches_each_submitted_attribute_once_and_skips_unused_lists():
    calls = []
    field_rules = (
        rules()
        | rules("value_id", "breed", "LIVESTOCK_BREED")
        | rules("value_code", "language", "LANGUAGE")
    )

    async def post(path, *, payload, pagination):
        calls.append(payload["attribute_id"])
        return [
            {
                "attribute_id": payload["attribute_id"],
                "value_code": "MALE",
                "value_id": 42,
            }
        ]

    assert (
        asyncio.run(
            validation.check_attribute_values(
                [{"gender": "MALE", "breed": "42"}] * 4, field_rules, say, post
            )
        )
        == []
    )
    assert calls == ["GENDER", "LIVESTOCK_BREED"]


def test_pages_only_the_requested_attribute():
    calls = []

    async def post(path, *, payload, pagination):
        calls.append((payload["attribute_id"], pagination["current_page"]))
        if pagination["current_page"] == 1:
            return [
                {"attribute_id": "GENDER", "value_code": "MALE", "value_id": 10}
            ] * 1000
        return [{"attribute_id": "GENDER", "value_code": "FEMALE", "value_id": 11}]

    assert (
        asyncio.run(
            validation.check_attribute_values(
                [{"gender": "FEMALE"}], rules(), say, post
            )
        )
        == []
    )
    assert calls == [("GENDER", 1), ("GENDER", 2)]


@pytest.mark.parametrize(
    "response", [None, {}, [{"attribute_id": "OTHER", "value_code": "MALE"}]]
)
def test_missing_or_malformed_lists_fail_closed(response):
    async def post(*args, **kwargs):
        return response

    problems = asyncio.run(
        validation.check_attribute_values([{"gender": "MALE"}], rules(), say, post)
    )
    assert len(problems) == 1 and problems[0].startswith("Gender: Master Data Service")


def test_unreachable_mds_names_service_and_does_not_leak_transport_details():
    async def post(*args, **kwargs):
        raise TimeoutError("private transport detail")

    problems = asyncio.run(
        validation.check_attribute_values([{"gender": "MALE"}], rules(), say, post)
    )
    assert problems == [say("oan_rule_mds_unavailable", label="Gender")]
    assert "private transport" not in problems[0]


def test_omitted_or_empty_optional_field_does_not_call_mds():
    async def post(*args, **kwargs):
        pytest.fail("No lookup for absent choices")

    assert (
        asyncio.run(
            validation.check_attribute_values(
                [{}, {"gender": None}, {"gender": ""}], rules(), say, post
            )
        )
        == []
    )


def test_request_catalog_is_not_reused_after_mds_failure():
    responses = iter(
        [[{"attribute_id": "GENDER", "value_code": "MALE", "value_id": 10}], None]
    )

    async def post(*args, **kwargs):
        return next(responses)

    async def run():
        assert (
            await validation.check_attribute_values(
                [{"gender": "MALE"}], rules(), say, post
            )
            == []
        )
        assert await validation.check_attribute_values(
            [{"gender": "MALE"}], rules(), say, post
        )

    asyncio.run(run())


@pytest.mark.parametrize("year", [1900, 2026, 2026.0, "2026", "2026.0"])
def test_acquisition_year_in_range(year):
    assert (
        validation.check_domain_bounds(
            [{"year_of_acquisition": year}], "Land", {}, say, date(2026, 10, 25)
        )
        == []
    )


@pytest.mark.parametrize("year", [1899, 2027, True, "bad", 2025.5])
def test_acquisition_year_outside_range(year):
    assert validation.check_domain_bounds(
        [{"year_of_acquisition": year}], "Land", {}, say, date(2026, 10, 25)
    ) == [
        "Year of Acquisition: enter a whole year from 1900 to 2026, or leave it empty."
    ]


def test_count_date_today_and_future():
    assert (
        validation.check_domain_bounds(
            [{"collected_date": "2026-10-25"}], "Livestock", {}, say, date(2026, 10, 25)
        )
        == []
    )
    assert validation.check_domain_bounds(
        [{"collected_date": "2026-10-26"}], "Livestock", {}, say, date(2026, 10, 25)
    ) == ["Count Date: the date is in the future. Choose today or an earlier date."]
