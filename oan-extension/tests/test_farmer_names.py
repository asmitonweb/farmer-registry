"""Tests for the farmer's names in other languages (FarmerNameService,
services/registers.py). They need the registry platform, so they run inside
the staff API image and are skipped elsewhere."""

import asyncio

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException

from openg2p_registry_oan_extension.register_domain.services.registers import (
    FarmerNameService,
)


def _validate(*records: dict) -> list[dict]:
    rows = [dict(r) for r in records]
    asyncio.run(FarmerNameService().validate_domain_attributes(rows))
    return rows


def _refused(*records: dict) -> str:
    with pytest.raises(G2PRegistryException) as error:
        _validate(*records)
    return error.value.message


OROMO = {"language": "AFAAN_OROMO", "first_name": "Caaltuu", "middle_name": "Gammachuu", "last_name": "Tolaa"}


def test_a_name_in_any_language_and_script_is_kept_with_tidy_spacing():
    rows = _validate({**OROMO, "first_name": "  Caaltuu "},
                     {"language": "TIGRINYA", "first_name": "ሃብቶም  ገብሩ"})
    assert rows[0]["first_name"] == "Caaltuu"
    assert rows[1]["first_name"] == "ሃብቶም ገብሩ"


def test_the_language_name_is_kept_only_for_other():
    rows = _validate({**OROMO, "language_name": "Oromo"},
                     {"language": "OTHER", "language_name": " Bench ", "first_name": "Shasha"})
    assert rows[0]["language_name"] is None
    assert rows[1]["language_name"] == "Bench"


def test_a_row_without_a_language_is_refused():
    assert _refused({"first_name": "Caaltuu"}).startswith("Language: a name row has no language")


def test_amharic_and_english_belong_in_the_name_section():
    assert "go in the Name section" in _refused({"language": "AMHARIC", "first_name": "አበበ"})
    assert "go in the Name section" in _refused({"language": "ENGLISH", "first_name": "Abebe"})


def test_other_needs_the_language_name():
    assert _refused({"language": "OTHER", "first_name": "Shasha"}).startswith("Language Name: the row's language is Other")


def test_a_row_without_a_first_name_is_refused_naming_the_language():
    message = _refused({"language": "SOMALI", "middle_name": "Cali"})
    assert message.startswith("First Name: the Somali name row has no first name")


def test_the_same_language_twice_is_refused():
    assert "Afaan Oromo is listed twice" in _refused(OROMO, {**OROMO, "first_name": "Lensa"})
    _validate({"language": "OTHER", "language_name": "Bench", "first_name": "A"},
              {"language": "OTHER", "language_name": "Sheko", "first_name": "B"})


def test_search_and_record_name_are_the_names():
    service = FarmerNameService()
    assert service.construct_search_text(OROMO) == "Caaltuu Gammachuu Tolaa"
    assert service.construct_record_name({"language": "SOMALI"}) == "Name"
