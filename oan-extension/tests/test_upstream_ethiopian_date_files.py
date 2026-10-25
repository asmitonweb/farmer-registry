"""The upstream calendar is vendored without edits until the platform ships it."""

import hashlib
from pathlib import Path

import pytest

OVERRIDES = Path(__file__).parents[2] / "ui/staff-ui/overrides"
UPSTREAM_FILES = {
    "src/features/activity/components/EthiopianDateInput.tsx": "1c4f40e569e78945af9ecda6d955d961d37eb7d1c07e953a5b61900a0731a8c8",
    "src/features/activity/utils/ethiopianCalendar.ts": "20445c685b8af2277ce2efe533b36aae0124646044fe5a54ed691b279ae5b89c",
}


@pytest.mark.parametrize("path,digest", UPSTREAM_FILES.items())
def test_upstream_calendar_bytes_are_unchanged(path, digest):
    assert hashlib.sha256((OVERRIDES / path).read_bytes()).hexdigest() == digest
    assert digest in (OVERRIDES / "src/features/activity/UPSTREAM.md").read_text()
