# Everything the farmer extension provides, then OAN's additions below. Core
# resolves classes by name on this module, so a name defined here wins.
import asyncio
import json
import time

from openg2p_fastapi_common.context import dbengine
from openg2p_registry_core.services import G2PRegisterDomainService
from openg2p_registry_farmer_extension.register_domain import services as _farmer
from openg2p_registry_farmer_extension.register_domain.services import *
from openg2p_registry_farmer_extension.register_domain.services.domain_validation_utils import (
    validation_error,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from .derivations import DERIVATIONS, Derivations
from .registers import FarmerPhoneService
from .widget_rules import Rules, check_record, collect_rules

# Section metadata is seed data that can change without a restart.
_RULES_TTL_SECONDS = 300
_cache: dict = {"at": 0.0, "rules": {}, "registers": {}, "messages": {}}
_lock = asyncio.Lock()


def _json(value):
    # Raw SQL through asyncpg returns json and jsonb columns as text.
    return json.loads(value) if isinstance(value, str) else value


async def _load() -> tuple[Rules, dict[str, str], dict[str, str]]:
    if time.monotonic() - _cache["at"] < _RULES_TTL_SECONDS:
        return _cache["rules"], _cache["registers"], _cache["messages"]
    async with _lock:
        if time.monotonic() - _cache["at"] >= _RULES_TTL_SECONDS:
            async with async_sessionmaker(dbengine.get())() as session:
                sections = (await session.execute(text(
                    "SELECT section_register_id, section_ui_schema FROM g2p_register_sections"))).all()
                registers = (await session.execute(text(
                    "SELECT register_mnemonic, register_id FROM g2p_register_definitions"))).all()
                messages = (await session.execute(text(
                    "SELECT domain_translation FROM registry_languages WHERE is_default"))).scalar()
            _cache.update(
                at=time.monotonic(),
                rules=collect_rules((r[0], _json(r[1])) for r in sections),
                registers={r[0]: r[1] for r in registers},
                messages=_json(messages) or {},
            )
    return _cache["rules"], _cache["registers"], _cache["messages"]


class WidgetRuleValidation:
    """Adds the derived values and the section widgets' value rules to a
    register's domain checks: derive first, so the farmer checks see them."""

    _derive_first = False

    async def validate_domain_attributes(self, records: list[dict]):
        if type(self)._derive_first:
            await self.derive(records)
        if type(self)._upstream_validates:
            await super().validate_domain_attributes(records)
        rules, registers, messages = await _load()
        field_rules = rules.get(registers.get(self.register_mnemonic()), {})
        if not field_rules:
            return
        problems = [p for record in records for p in check_record(record, field_rules, messages)]
        if problems:
            validation_error("; ".join(dict.fromkeys(problems)))


_PREFIX = "G2PRegisterDomainService"


def _with_widget_rules(name: str, base: type) -> type:
    upstream = base.validate_domain_attributes is not G2PRegisterDomainService.validate_domain_attributes
    derivations = DERIVATIONS.get(name[len(_PREFIX):], Derivations)
    return type(name, (WidgetRuleValidation, derivations, base),
                {"__module__": __name__, "_upstream_validates": upstream, "_derive_first": True})


# One subclass per farmer domain service, under the same name, so every
# register, including one the farmer extension adds later, gets the rules.
for _name in dir(_farmer):
    _base = getattr(_farmer, _name)
    if (
        _name.startswith(_PREFIX)
        and isinstance(_base, type)
        and issubclass(_base, G2PRegisterDomainService)
        and _base is not G2PRegisterDomainService
    ):
        globals()[_name] = _with_widget_rules(_name, _base)

# OAN's own registers.
for _name, _service in (("FarmerPhone", FarmerPhoneService),):
    globals()[_PREFIX + _name] = type(_PREFIX + _name, (WidgetRuleValidation, _service),
                                      {"__module__": __name__, "_upstream_validates": True})
