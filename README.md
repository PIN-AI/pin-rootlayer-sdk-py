# pin-rootlayer-sdk (Python)

Python SDK for PIN RootLayer:

- Generate signatures compatible with current RootLayer/IntentManager verification (**EIP-191 / `signMessage` over `keccak256(abi.encode(...))`**)
- Call RootLayer HTTP endpoints (sync + async)
- Agent Direct Mode runtime (gRPC): `AgentConnect` stream + `Heartbeat` + `SubmitDirectResult`
- Accept `bytes` fields as `bytes`, base64 string, or `0x` hex string

## Install

```bash
pip install "git+https://github.com/PIN-AI/pin-rootlayer-sdk-py.git"
```

For development:

```bash
git clone https://github.com/PIN-AI/pin-rootlayer-sdk-py.git
cd pin-rootlayer-sdk-py
pip install -e ".[dev]"
```

## Quickstart (signer + RootLayer URL)

```python
from pin_rootlayer_sdk import (
    ChainConfig,
    IntentParams,
    PrivateKeySigner,
    RootLayerClient,
    SubmitDirectIntentRequest,
)

signer = PrivateKeySigner("0x...your_private_key...")

client = RootLayerClient(
    "http://127.0.0.1:8000",
    signer=signer,
    chains={
        "base_sepolia": ChainConfig(
            chain_id=84532,
            intent_manager_address="0xYourIntentManagerAddress",
        )
    },
)

resp = client.submit_direct_intent(
    SubmitDirectIntentRequest(
        intent_id="0x" + "11" * 32,
        subnet_id="0x" + "00" * 31 + "01",
        requester=signer.address,  # optional if client has signer
        settle_chain="base_sepolia",
        intent_type="test",
        params=IntentParams(intent_raw=b"pingraw", metadata=b"-test meta-"),
        deadline=1822275330,
        payment_token="0x0000000000000000000000000000000000000000",
        amount="0",
        target_agent="0xTargetAgentAddress",
        target_agent_id="1",  # ERC-8004 tokenId
    )
)

print(resp.ok, resp.intent_id, resp.status)

## Agent Direct Mode (gRPC): AgentConnect V2 + heartbeat

```python
from pin_rootlayer_sdk import PrivateKeySigner
from pin_rootlayer_sdk.rootlayer_agent import RootLayerAgentClient

signer = PrivateKeySigner("0x...your_private_key...")

# gRPC target (host:port), e.g. "127.0.0.1:9000"
with RootLayerAgentClient("127.0.0.1:9000", signer=signer) as client:
    session = client.agent_connect(agent_id="1", client_version="my-agent/0.1.0")
    session.start_heartbeat(interval_s=10)

    while True:
        push = session.recv()  # blocks

        # TODO: execute the task in push.params / push.intent_type
        result = b"ok"

        session.submit_direct_result_from_push(
            push,
            result_data=result,
            success=True,
            error_message="",
        )
```
```

## Standard (auction) intent

```python
from pin_rootlayer_sdk import ChainConfig, IntentParams, PrivateKeySigner, RootLayerClient, SubmitIntentRequest

signer = PrivateKeySigner("0x...your_private_key...")

client = RootLayerClient(
    "http://127.0.0.1:8000",
    signer=signer,
    chains={
        "base_sepolia": ChainConfig(
            chain_id=84532,
            intent_manager_address="0xYourIntentManagerAddress",
        )
    },
)

resp = client.submit_intent(
    SubmitIntentRequest(
        intent_id="0x" + "11" * 32,
        subnet_id="0x" + "00" * 31 + "01",
        requester=signer.address,  # optional if client has signer
        settle_chain="base_sepolia",
        intent_type="test",
        params=IntentParams(intent_raw=b"pingraw", metadata=b"-test meta-"),
        deadline=1822275330,
        budget_token="0x0000000000000000000000000000000000000000",
        budget="0",
    )
)

print(resp.ok, resp.intent_id, resp.intent_expiration)
```

## MetaMask signing (browser) + submit from Python

RootLayer signatures are **EIP-191 `signMessage`** over the SDK-computed 32-byte digest (not EIP-712 typed data).

### 1) Backend: build request + compute digest

```python
from pin_rootlayer_sdk import ChainConfig, IntentParams, SubmitDirectIntentRequest
from pin_rootlayer_sdk.signing import direct_intent_digest, params_hash

chain = ChainConfig(chain_id=84532, intent_manager_address="0xYourIntentManagerAddress")

req = SubmitDirectIntentRequest(
    intent_id="0x" + "11" * 32,
    subnet_id="0x" + "00" * 31 + "01",
    requester="0xYourEOAAddress",  # the address expected to sign
    settle_chain="base_sepolia",
    intent_type="test",
    params=IntentParams(intent_raw=b"pingraw", metadata=b"-test meta-"),
    deadline=1822275330,
    payment_token="0x0000000000000000000000000000000000000000",
    amount="0",
    target_agent="0xTargetAgentAddress",
    target_agent_id="1",  # ERC-8004 tokenId
)

ph = params_hash(req.params.intent_raw, req.params.metadata or b"")
digest32 = direct_intent_digest(
    intent_id=req.intent_id,
    subnet_id=req.subnet_id,
    requester=req.requester,
    intent_type=req.intent_type,
    params_hash_=ph,
    deadline=int(req.deadline),
    payment_token=req.payment_token,
    amount=int(req.amount),
    target_agent=req.target_agent,
    intent_manager=chain.intent_manager_address,
    chain_id=chain.chain_id,
)

digest_hex = "0x" + digest32.hex()  # send this to the frontend
```

### 2) Frontend: MetaMask sign (ethers v6)

```ts
import { ethers } from "ethers";

const provider = new ethers.BrowserProvider(window.ethereum);
await provider.send("eth_requestAccounts", []);
const signer = await provider.getSigner();

// digestHex is the 0x-prefixed 32-byte hex string from the backend
const signatureHex = await signer.signMessage(ethers.getBytes(digestHex));
```

### 3) Backend: submit with provided signature

```python
from pin_rootlayer_sdk import RootLayerClient

client = RootLayerClient(
    "http://127.0.0.1:8000",
    chains={"base_sepolia": chain},
)

req.signature = signatureHex  # accepts 0x hex / base64 / bytes
resp = client.submit_direct_intent(req)
```

## Async

```python
import asyncio

from pin_rootlayer_sdk import AsyncRootLayerClient, ChainConfig, PrivateKeySigner


async def main():
    signer = PrivateKeySigner("0x...")
    async with AsyncRootLayerClient(
        "http://127.0.0.1:8000",
        signer=signer,
        chains={"base_sepolia": ChainConfig(chain_id=84532, intent_manager_address="0x...")},
    ) as client:
        resp = await client.submit_direct_intent(
            {
                "intent_id": "0x" + "11" * 32,
                "subnet_id": "0x" + "00" * 31 + "01",
                "settle_chain": "base_sepolia",
                "intent_type": "test",
                "params": {"intent_raw": "0x70696e67726177"},
                "deadline": 1822275330,
                "amount": "0",
                "target_agent": "0xTargetAgentAddress",
                "target_agent_id": "1",
            }
        )
        print(resp.ok, resp.intent_id)


asyncio.run(main())
```

## Docs

- `docs/signing.md` — digests and signature rules
- `docs/http.md` — supported HTTP endpoints

