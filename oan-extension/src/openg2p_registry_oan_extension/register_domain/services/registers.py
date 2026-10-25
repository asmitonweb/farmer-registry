"""Domain service of OAN's own child register (models/registers.py)."""

from openg2p_registry_core.services import G2PRegisterDomainService
from openg2p_registry_farmer_extension.register_domain.services.domain_validation_utils import (
    as_bool,
    is_blank,
    validation_error,
)

from ..derived import normalize_phone
from .derivations import Derivations, refresh_farmer, refresh_farmers_of


def _join(payload: dict, keys) -> str:
    return " ".join(str(payload.get(k)).strip() for k in keys if not is_blank(payload.get(k)))


class FarmerPhoneService(Derivations, G2PRegisterDomainService):
    """A farmer's phone numbers. Kept as the national number plus E.164, one
    number once per farmer, at most one primary; the farmer's phone list
    follows them."""

    async def validate_domain_attributes(self, records: list[dict]):
        await self.derive(records)
        primaries, numbers = 0, set()
        for record in records:
            if is_blank(record.get("phone_number")):
                validation_error("Phone Number: a row has no number. Enter the number, or remove the row")
            if record.get("is_primary"):
                primaries += 1
            if record["phone_number"] in numbers:
                validation_error("Phone Number: the same number is listed twice. Keep one row for it and remove the other")
            numbers.add(record["phone_number"])
        if primaries > 1:
            validation_error("Primary: more than one number is marked primary. Tick Primary for one number only")

    async def derive(self, records: list[dict]) -> None:
        for record in records:
            if "is_primary" in record:
                record["is_primary"] = bool(as_bool(record.get("is_primary")))
            if is_blank(record.get("phone_number")):
                continue
            if is_blank(record.get("country_code")):
                record["country_code"] = "ET"
            national, e164 = normalize_phone(record["phone_number"], record["country_code"])
            if national is None:
                validation_error(f"Phone Number: {record['phone_number']} is not a phone number. Enter it as 0912345678 or +251912345678")
            record["phone_number"], record["phone_e164"] = national, e164

    async def pre_approve(self, change_request, session):
        await self.derive_payload(change_request, session)

    async def post_approve(self, change_request, session):
        await refresh_farmers_of(change_request, session)

    async def post_ingest(self, register_id, register_row, session):
        national, e164 = normalize_phone(register_row.phone_number, register_row.country_code)
        if national:
            register_row.phone_number, register_row.phone_e164 = national, e164
        await refresh_farmer(session, register_row.link_internal_record_id)

    def construct_search_text(self, payload: dict, extra: list[str] | None = None) -> str:
        return " ".join([*(extra or []), _join(payload, ("phone_type", "phone_number", "phone_e164"))]).strip()

    def construct_record_name(self, payload: dict, extra: list[str] | None = None) -> str:
        return " ".join([*(extra or []), _join(payload, ("phone_type", "phone_number"))]).strip() or "Phone"


# Languages whose names the Name section asks itself: English is upstream's
# first, middle and last name, Amharic the *_amh fields Fayda fills in.
NAME_SECTION_LANGUAGES = {"ENGLISH", "AMHARIC"}
OTHER_LANGUAGE = "OTHER"
NAME_FIELDS = ("first_name", "middle_name", "last_name")


def _language(code: str) -> str:
    """AFAAN_OROMO as Afaan Oromo, for messages."""
    return str(code).replace("_", " ").title()


def _tidy(value):
    return " ".join(str(value).split()) if not is_blank(value) else None


class FarmerNameService(Derivations, G2PRegisterDomainService):
    """A farmer's name in a language other than English and Amharic, one row
    per language. Names are kept as typed, in any script; only spacing is
    tidied. The farmer's other_language_names follow the rows, so the farmer
    is found by them."""

    async def validate_domain_attributes(self, records: list[dict]):
        await self.derive(records)
        seen = set()
        for record in records:
            language = record.get("language")
            if is_blank(language):
                validation_error("Language: a name row has no language. Choose the language the name is written in, or remove the row")
            if language in NAME_SECTION_LANGUAGES:
                validation_error(
                    f"Language: {_language(language)} names go in the Name section, not in Names in Other Languages. "
                    "Enter them there and remove this row")
            if language == OTHER_LANGUAGE and is_blank(record.get("language_name")):
                validation_error("Language Name: the row's language is Other. Enter the name of the language")
            shown = record.get("language_name") if language == OTHER_LANGUAGE else _language(language)
            if is_blank(record.get("first_name")):
                validation_error(f"First Name: the {shown} name row has no first name. Enter it, or remove the row")
            key = (language, str(record.get("language_name") or "").casefold())
            if key in seen:
                validation_error(f"Language: {shown} is listed twice. Keep one row for it and remove the other")
            seen.add(key)

    async def derive(self, records: list[dict]) -> None:
        for record in records:
            for field in (*NAME_FIELDS, "language_name"):
                if field in record:
                    record[field] = _tidy(record[field])
            if "language" in record and record.get("language") != OTHER_LANGUAGE:
                record["language_name"] = None

    async def pre_approve(self, change_request, session):
        await self.derive_payload(change_request, session)

    async def post_approve(self, change_request, session):
        await refresh_farmers_of(change_request, session)

    async def post_ingest(self, register_id, register_row, session):
        for field in NAME_FIELDS:
            setattr(register_row, field, _tidy(getattr(register_row, field)))
        await refresh_farmer(session, register_row.link_internal_record_id)

    def construct_search_text(self, payload: dict, extra: list[str] | None = None) -> str:
        return " ".join([*(extra or []), _join(payload, NAME_FIELDS)]).strip()

    def construct_record_name(self, payload: dict, extra: list[str] | None = None) -> str:
        return " ".join([*(extra or []), _join(payload, NAME_FIELDS)]).strip() or "Name"
