"""The household on a farmer's intake form, checked when the form is finalized.

A new farmer's household is either one already registered, picked in the
household lookup (the farmer's link_internal_record_id), or a new one, entered
in the household sections of the same form; the household is then created with
the farmer on approval. The per-section hooks only see the section being saved,
so the whole form is checked at finalize, the way the farmer extension checks a
household's own intake form (household_submission_validation): exactly one of
the two, and a new household's members by the farmer extension's roster rules.
"""

from openg2p_registry_farmer_extension.register_domain.services import (
    G2PFarmerIntakeFormDataService,
)
from openg2p_registry_farmer_extension.register_domain.services.domain_validation_utils import (
    is_blank,
    validation_error,
)
from openg2p_registry_farmer_extension.register_domain.services.household_submission_validation import (
    validate_household_roster,
)
from sqlalchemy import select

FARMER_REGISTER_MNEMONIC = "Farmer"

MESSAGES = {
    "oan_household_both": (
        "Household: an existing household is picked in the household lookup and a new household is "
        "entered as well. Keep one: clear the household lookup to register the new household, or clear "
        "the household information and members to join the picked one."
    ),
    "oan_household_none": (
        "Household: none is given. Pick the farmer's household in the household lookup, or enter a new "
        "household in the household information and members."
    ),
}


def _say(messages: dict, key: str) -> str:
    return messages.get(key) or MESSAGES[key]


def _get(row, key: str):
    return row.get(key) if isinstance(row, dict) else getattr(row, key, None)


def check_farmer_household(farmers: list, household, members: list, messages: dict | None = None) -> None:
    """Exactly one household for the farmer; a new one with a valid roster.

    `farmers`, `household` and `members` may be ORM rows or plain dicts.
    Raises the platform validation error on the first breach.
    """
    messages = messages or {}
    new_id = _get(household, "internal_record_id") if household is not None else None
    picked = [
        link for link in (_get(farmer, "link_internal_record_id") for farmer in farmers)
        if not is_blank(link) and link != new_id
    ]
    if household is None:
        if not picked and not members:
            validation_error(_say(messages, "oan_household_none"))
        if not picked:
            # Members without the household information: upstream's roster
            # check says the information is missing.
            validate_household_roster(None, members)
        return
    if picked:
        validation_error(_say(messages, "oan_household_both"))
    validate_household_roster(household, members)


class OANIntakeFormDataService(G2PFarmerIntakeFormDataService):
    """The farmer extension's intake service, with the farmer household check."""

    async def finalize_submission_with_session(self, submission_id: str, session, *args, **kwargs):
        submission = await self._get_submission_or_error(submission_id, session)
        register_definition = await self._get_register_definition(submission.register_id, session)
        if getattr(register_definition, "register_mnemonic", None) == FARMER_REGISTER_MNEMONIC:
            await check_farmer_submission(submission.submission_id, session)
        return await super().finalize_submission_with_session(submission_id, session, *args, **kwargs)


async def check_farmer_submission(submission_id: str, session) -> None:
    # Lazy: the models import the services package when they load.
    from openg2p_registry_extensions.register_domain.models import (
        G2PIntakeFormFarmer,
        G2PIntakeFormHousehold,
        G2PIntakeFormHouseholdMember,
    )

    from . import _load, _reworded

    async def rows(cls):
        result = await session.execute(select(cls).where(cls.submission_id == str(submission_id)))
        return list(result.scalars().all())

    farmers = await rows(G2PIntakeFormFarmer)
    households = await rows(G2PIntakeFormHousehold)
    members = await rows(G2PIntakeFormHouseholdMember)
    _, _, messages = await _load()
    async with _reworded(messages):
        check_farmer_household(farmers, households[0] if households else None, members, messages)


def install_farmer_household_check() -> OANIntakeFormDataService:
    """Put OAN's intake service ahead of every other one: get_component()
    returns the first registered instance (the farmer extension does the same)."""
    from openg2p_fastapi_common.context import component_registry
    from openg2p_registry_core.services.intake_form_data_service import (
        G2PIntakeFormDataService,
    )

    current = G2PIntakeFormDataService.get_component()
    if isinstance(current, OANIntakeFormDataService):
        return current
    service = OANIntakeFormDataService()
    component_registry.remove(service)
    first = next((i for i, c in enumerate(component_registry) if isinstance(c, G2PIntakeFormDataService)),
                 len(component_registry))
    component_registry.insert(first, service)
    return service
