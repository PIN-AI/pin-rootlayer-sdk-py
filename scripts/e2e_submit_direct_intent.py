from __future__ import annotations

import argparse
import os
import pathlib
import secrets
import sys
import time

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
sys.path.insert(0, str(_SRC))

from pin_rootlayer_sdk import (  # noqa: E402
    ChainConfig,
    IntentParams,
    PrivateKeySigner,
    RootLayerClient,
)
from pin_rootlayer_sdk.models import SubmitDirectIntentRequest  # noqa: E402
from pin_rootlayer_sdk.signing import direct_intent_digest, params_hash  # noqa: E402


def _required_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"missing env var: {name}")
    return v


def main() -> None:
    parser = argparse.ArgumentParser(
        description="E2E: compute digest -> sign -> submit Direct Mode intent to RootLayer",
    )
    parser.add_argument(
        "--rootlayer-url",
        default=os.getenv("ROOTLAYER_URL", "localhost:8000"),
        help="RootLayer HTTP base URL (env: ROOTLAYER_URL)",
    )
    parser.add_argument(
        "--settle-chain",
        default=os.getenv("SETTLE_CHAIN", "base_sepolia"),
        help="Settle chain name used by RootLayer routing (env: SETTLE_CHAIN)",
    )
    parser.add_argument(
        "--intent-type",
        default=os.getenv("INTENT_TYPE", "weather_query"),
        help="Intent type (env: INTENT_TYPE)",
    )
    parser.add_argument(
        "--intent-raw",
        default=os.getenv("INTENT_RAW", '{"city":"New York"}'),
        help="Intent raw bytes (env: INTENT_RAW)",
    )
    parser.add_argument(
        "--metadata",
        default=os.getenv("METADATA", ""),
        help="Metadata bytes (env: METADATA)",
    )
    parser.add_argument(
        "--payment-token",
        default=os.getenv("PAYMENT_TOKEN", "0x0000000000000000000000000000000000000000"),
        help="Payment token (env: PAYMENT_TOKEN)",
    )
    parser.add_argument(
        "--amount",
        default=os.getenv("AMOUNT", "0"),
        help="Payment amount (env: AMOUNT)",
    )
    parser.add_argument(
        "--deadline-seconds",
        type=int,
        default=int(os.getenv("DEADLINE_SECONDS", "3600")),
        help="Deadline seconds from now (env: DEADLINE_SECONDS)",
    )
    args = parser.parse_args()

    private_key = _required_env("PRIVATE_KEY")
    subnet_id = _required_env("SUBNET_ID")
    target_agent = _required_env("TARGET_AGENT")
    target_agent_id = _required_env("TARGET_AGENT_ID")
    intent_manager_address = _required_env("INTENT_MANAGER_ADDRESS")
    chain_id = int(_required_env("CHAIN_ID"))

    signer = PrivateKeySigner(private_key)
    chain = ChainConfig(chain_id=chain_id, intent_manager_address=intent_manager_address)

    intent_id = "0x" + secrets.token_hex(32)
    deadline = int(time.time()) + args.deadline_seconds

    req = SubmitDirectIntentRequest(
        intent_id=intent_id,
        subnet_id=subnet_id,
        requester=signer.address,
        settle_chain=args.settle_chain,
        intent_type=args.intent_type,
        params=IntentParams(
            intent_raw=args.intent_raw.encode("utf-8"),
            metadata=args.metadata.encode("utf-8") if args.metadata else b"",
        ),
        payment_token=args.payment_token,
        amount=args.amount,
        deadline=deadline,
        target_agent=target_agent,
        target_agent_id=target_agent_id,
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

    client = RootLayerClient(
        args.rootlayer_url,
        chains={args.settle_chain: chain},
    )
    try:
        resp = client.submit_direct_intent(req)
    finally:
        client.close()

    print("ok:", resp.ok)
    print("intent_id:", resp.intent_id)
    print("status:", resp.status)
    print("msg:", resp.msg)


if __name__ == "__main__":
    main()
