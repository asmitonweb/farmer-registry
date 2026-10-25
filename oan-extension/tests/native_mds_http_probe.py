"""Run OAN validation through the installed native client and real HTTP.

Run inside the native staff API image with /work mounted to this checkout and
MDS_TEST_URL pointing to the local Postman simulation's /master-data address.
No production credentials or databases are used.
"""

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from openg2p_registry_core.helpers.master_data import MasterDataClient

ROOT = Path(
    "/work/oan-extension/src/openg2p_registry_oan_extension/register_domain/services"
)


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validation, widgets = load("attribute_validation"), load("widget_rules")


class LocalMasterDataClient(MasterDataClient):
    def _settings(self):
        return SimpleNamespace(
            master_data_api_url=os.environ["MDS_TEST_URL"],
            master_data_timeout_seconds=2,
        )


async def main():
    client = LocalMasterDataClient()
    say = widgets._Say({"gender": "Gender", "breed": "Breed"})
    rules = {
        "gender": {"master_data": {"attribute_id": "GENDER", "value_key": "value_code"}}
    }
    check = validation.check_attribute_values
    if sys.argv[1] != "success":
        errors = await check([{"gender": "MALE"}], rules, say, client._post)
        assert errors == [say("oan_rule_mds_unavailable", label="Gender")], errors
        print("PASS native HTTP fail-closed:", sys.argv[1])
        return
    assert await check([{"gender": "MALE"}] * 3, rules, say, client._post) == []
    assert await check([{"gender": "unknown"}], rules, say, client._post) == [
        say("oan_rule_option", label="Gender", value="unknown")
    ]
    rules = {
        "breed": {
            "master_data": {"attribute_id": "LIVESTOCK_BREED", "value_key": "value_id"}
        }
    }
    assert await check([{"breed": 42}, {"breed": "42"}], rules, say, client._post) == []
    assert await check([{"breed": "LOCAL"}], rules, say, client._post) == [
        say("oan_rule_option", label="Breed", value="LOCAL")
    ]
    print("PASS native HTTP: code success/error, ID success/error, batched rows")


if __name__ == "__main__":
    asyncio.run(main())
