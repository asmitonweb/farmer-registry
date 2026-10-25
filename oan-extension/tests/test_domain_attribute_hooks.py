"""Run the registered OAN domain hook in the native platform test runtime."""

import asyncio
from datetime import date
from types import SimpleNamespace

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.errors import G2PRegistryException
from openg2p_registry_oan_extension.register_domain import services


def setup_hook(monkeypatch, post):
    rules = {
        "land": {
            "means_of_acquisition": {
                "label": "means_of_acquisition",
                "master_data": {
                    "attribute_id": "MEANS_OF_ACQUISITION",
                    "value_key": "value_id",
                },
            }
        }
    }

    async def load():
        return rules, {"Land": "land"}, {"means_of_acquisition": "Means of Acquisition"}

    monkeypatch.setattr(services, "_load", load)
    monkeypatch.setattr(
        services.MasterDataClient,
        "get_component",
        classmethod(lambda cls: SimpleNamespace(_post=post)),
    )
    return object.__new__(services.G2PRegisterDomainServiceLand)


def test_registered_hook_checks_id_choices_and_mds_outage(monkeypatch):
    responses = iter(
        [
            [
                {
                    "attribute_id": "MEANS_OF_ACQUISITION",
                    "value_id": 42,
                    "value_code": "PURCHASE",
                }
            ],
            [
                {
                    "attribute_id": "MEANS_OF_ACQUISITION",
                    "value_id": 42,
                    "value_code": "PURCHASE",
                }
            ],
            None,
        ]
    )

    async def post(*args, **kwargs):
        return next(responses)

    service = setup_hook(monkeypatch, post)

    async def run():
        await service.validate_domain_attributes([{"means_of_acquisition": "42"}])
        with pytest.raises(G2PRegistryException) as bad_choice:
            await service.validate_domain_attributes(
                [{"means_of_acquisition": "PURCHASE"}]
            )
        assert (
            'Means of Acquisition: "PURCHASE" is not one of the choices'
            in bad_choice.value.message
        )
        with pytest.raises(G2PRegistryException) as unavailable:
            await service.validate_domain_attributes([{"means_of_acquisition": "42"}])
        assert "Means of Acquisition: Master Data Service" in unavailable.value.message

    asyncio.run(run())


def test_registered_hook_enforces_acquisition_year_without_mds(monkeypatch):
    async def post(*args, **kwargs):
        pytest.fail("No MDS-bound field submitted")

    service = setup_hook(monkeypatch, post)

    async def run():
        await service.validate_domain_attributes(
            [{"year_of_acquisition": date.today().year}]
        )
        with pytest.raises(G2PRegistryException) as out_of_range:
            await service.validate_domain_attributes([{"year_of_acquisition": 1899}])
        assert "1900" in out_of_range.value.message

    asyncio.run(run())
