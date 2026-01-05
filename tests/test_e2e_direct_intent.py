from __future__ import annotations

import os
import secrets
import time

import pytest

from pin_rootlayer_sdk import ChainConfig, IntentParams, PrivateKeySigner, RootLayerClient
from pin_rootlayer_sdk.models import SubmitDirectIntentRequest
from pin_rootlayer_sdk.signing import direct_intent_digest, params_hash


def _env(name: str) -> str | None:
    v = os.getenv(name)
    return v if v else None


@pytest.mark.e2e
def test_e2e_submit_direct_intent() -> None:
    rootlayer_url = _env("ROOTLAYER_URL")
    private_key = _env("PRIVATE_KEY")
    subnet_id = _env("SUBNET_ID")
    target_agent = _env("TARGET_AGENT")
    intent_manager_address = _env("INTENT_MANAGER_ADDRESS")
    chain_id = _env("CHAIN_ID")
    settle_chain = _env("SETTLE_CHAIN") or "base_sepolia"

    if not all(
        [
            rootlayer_url,
            private_key,
            subnet_id,
            target_agent,
            intent_manager_address,
            chain_id,
        ]
    ):
        pytest.skip(
            "e2e env not configured (need ROOTLAYER_URL, PRIVATE_KEY, SUBNET_ID, TARGET_AGENT, "
            "INTENT_MANAGER_ADDRESS, CHAIN_ID)",
        )

    signer = PrivateKeySigner(private_key)
    chain = ChainConfig(chain_id=int(chain_id), intent_manager_address=intent_manager_address)

    req = SubmitDirectIntentRequest(
        intent_id="0x" + secrets.token_hex(32),
        subnet_id=subnet_id,
        requester=signer.address,
        settle_chain=settle_chain,
        intent_type=_env("INTENT_TYPE") or "e2e_test",
        params=IntentParams(intent_raw=b"e2e", metadata=b""),
        payment_token=_env("PAYMENT_TOKEN") or "0x0000000000000000000000000000000000000000",
        amount=_env("AMOUNT") or "0",
        deadline=int(time.time()) + int(_env("DEADLINE_SECONDS") or "3600"),
        target_agent=target_agent,
        signature=None,
    )

    ph = params_hash(req.params.intent_raw, req.params.metadata or b"")
    digest32 = direct_intent_digest(
        intent_id=req.intent_id,
        subnet_id=req.subnet_id,
        requester=req.requester or signer.address,
        intent_type=req.intent_type,
        params_hash_=ph,
        deadline=int(req.deadline),
        payment_token=req.payment_token,
        amount=int(req.amount),
        target_agent=req.target_agent,
        intent_manager=chain.intent_manager_address,
        chain_id=chain.chain_id,
    )
    req.signature = signer.sign_message_32(digest32)

    client = RootLayerClient(rootlayer_url, chains={settle_chain: chain})
    try:
        resp = client.submit_direct_intent(req)
    finally:
        client.close()

    assert resp.ok is True
    assert resp.intent_id
