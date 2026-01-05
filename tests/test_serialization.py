from __future__ import annotations

import base64

from pin_rootlayer_sdk.models import IntentParams, SubmitIntentRequest


def test_submit_intent_json_bytes_are_base64_and_camelcase() -> None:
    req = SubmitIntentRequest(
        intent_id="0x" + "11" * 32,
        subnet_id="0x" + "00" * 31 + "01",
        requester="0xF39fd6e51aad88F6F4ce6aB8827279cffFb92266",
        settle_chain="base_sepolia",
        intent_type="test",
        params=IntentParams(intent_raw=b"pingraw", metadata=b"-test meta-"),
        deadline=1822275330,
        signature=b"\x01" * 65,
        budget_token="0x0000000000000000000000000000000000000000",
        budget="0",
    )

    payload = req.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert "intentId" in payload
    assert "subnetId" in payload
    assert "budgetToken" in payload
    assert payload["params"]["intentRaw"] == base64.b64encode(b"pingraw").decode("ascii")
    assert payload["params"]["metadata"] == base64.b64encode(b"-test meta-").decode("ascii")
    assert payload["signature"] == base64.b64encode(b"\x01" * 65).decode("ascii")
