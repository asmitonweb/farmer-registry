# Master Data validation simulation

Local contract fixture, 2026-10-25. Source: native rc.557 `MasterDataClient` and
MDS `G2PAttributeController.get_attribute_values`. Owner mock search was skipped:
Postman CLI has no signed-in session. No cloud resources were created.

## Purpose

Run the OAN validator with the actual installed platform HTTP client against
code/ID choice lists, HTTP 503 and invalid JSON. Non-personal fixture values only.

## Execution

Start `postman simulation run postman/simulations/master-data-validation.sim.yaml
--port 4907 --no-history --output ndjson`. Use the addresses in its listening event.
Run the native staff API image with this checkout mounted at `/work:ro`, entrypoint
`python`, `MDS_TEST_URL=http://host.docker.internal:4907/master-data` and command
`/work/oan-extension/tests/native_mds_http_probe.py success`. Repeat with the
`master-data-unavailable` / `master-data-malformed` routes and matching mode.
For connection refusal use `--network none`, URL `http://127.0.0.1:9/master-data`,
mode `connection-refused`. Stop only this simulation with Ctrl+C.

## Assumptions

The catalog is scoped by MDS and fields keep their configured `valueKey`. Native
envelopes and pagination must be accepted by the fixture. Authentication is not
configured for this isolated test; live MDS permissions are outside this proof.

## Observations

<!-- begin:observations -->
2026-10-25: Native client/OAN probe exited 0 for code success/error, ID
success/error and batched rows (four HTTP 200 requests). Outage (HTTP 503), invalid
JSON (HTTP 200) and refused connection each exited 0 after verifying a fail-closed
field message. These are simulated dependency checks, not a live portal approval.
<!-- end:observations -->

## What didn't work

`simulation run --scenario unavailable` reports `--scenario requires --proxy`.
Separate path-routed members expose the fault fixtures without changing the
native client or replacing HTTP calls with stubs. The native image lacks pytest;
the full suite uses pytest in a temporary container directory, never an app pod.
