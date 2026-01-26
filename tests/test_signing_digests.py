from __future__ import annotations

from eth_utils import keccak, to_bytes

from pin_rootlayer_sdk.signer import PrivateKeySigner
from pin_rootlayer_sdk.signing import (
    AGENT_CONNECT_TYPEHASH,
    AGENT_CONNECT_TYPEHASH_DEF,
    ASSIGNMENT_TYPEHASH,
    ASSIGNMENT_TYPEHASH_DEF,
    DIRECT_INTENT_TYPEHASH,
    DIRECT_INTENT_TYPEHASH_DEF,
    INTENT_TYPEHASH,
    INTENT_TYPEHASH_DEF,
    VALIDATION_BATCH_TYPEHASH,
    VALIDATION_BATCH_TYPEHASH_DEF,
    VALIDATION_TYPEHASH,
    VALIDATION_TYPEHASH_DEF,
    agent_connect_digest,
    assignment_digest,
    direct_intent_digest,
    intent_digest,
    params_hash,
    recover_address,
    validation_batch_digest,
    validation_digest,
)


def _u256(x: int) -> bytes:
    return x.to_bytes(32, "big")


def _bytes32_hex(h: str) -> bytes:
    assert h.startswith("0x") and len(h) == 66
    return bytes.fromhex(h[2:])


def _addr32(addr: str) -> bytes:
    b = to_bytes(hexstr=addr)
    assert len(b) == 20
    return b.rjust(32, b"\x00")


def test_typehashes_match_keccak_text() -> None:
    assert INTENT_TYPEHASH == keccak(text=INTENT_TYPEHASH_DEF)
    assert ASSIGNMENT_TYPEHASH == keccak(text=ASSIGNMENT_TYPEHASH_DEF)
    assert VALIDATION_TYPEHASH == keccak(text=VALIDATION_TYPEHASH_DEF)
    assert VALIDATION_BATCH_TYPEHASH == keccak(text=VALIDATION_BATCH_TYPEHASH_DEF)
    assert DIRECT_INTENT_TYPEHASH == keccak(text=DIRECT_INTENT_TYPEHASH_DEF)
    assert AGENT_CONNECT_TYPEHASH == keccak(text=AGENT_CONNECT_TYPEHASH_DEF)


def test_intent_digest_manual_equivalence_and_signature_recovery() -> None:
    signer = PrivateKeySigner(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    assert signer.address.lower() == "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"

    intent_id = "0x" + "11" * 32
    subnet_id = "0x" + "00" * 31 + "01"
    intent_manager = "0xB7f8BC63BbcaD18155201308C8f3540b07f84F5e"
    chain_id = 31337

    ph = params_hash(b"pingraw", b"-test meta-")
    d1 = intent_digest(
        intent_id=intent_id,
        subnet_id=subnet_id,
        requester=signer.address,
        intent_type="test",
        params_hash_=ph,
        deadline=1822275330,
        budget_token="0x0000000000000000000000000000000000000000",
        budget=0,
        intent_manager=intent_manager,
        chain_id=chain_id,
    )

    typehash = keccak(text=INTENT_TYPEHASH_DEF)
    manual = keccak(
        b"".join(
            [
                typehash,
                _bytes32_hex(intent_id),
                _bytes32_hex(subnet_id),
                _addr32(signer.address),
                keccak(text="test"),
                ph,
                _u256(1822275330),
                _addr32("0x0000000000000000000000000000000000000000"),
                _u256(0),
                _addr32(intent_manager),
                _u256(chain_id),
            ]
        )
    )
    assert d1 == manual

    sig = signer.sign_message_32(d1)
    assert len(sig) == 65
    assert recover_address(d1, sig).lower() == signer.address.lower()


def test_assignment_digest_manual_equivalence() -> None:
    assignment_id = "0x" + "aa" * 32
    intent_id = "0x" + "bb" * 32
    bid_id = "0x" + "00" * 32
    agent = "0x9290085Cd66bD1A3C7D277EF7DBcbD2e98457b6f"
    matcher = "0xF39fd6e51aad88F6F4ce6aB8827279cffFb92266"
    intent_manager = "0xB7f8BC63BbcaD18155201308C8f3540b07f84F5e"
    chain_id = 31337

    d1 = assignment_digest(
        assignment_id=assignment_id,
        intent_id=intent_id,
        bid_id=bid_id,
        agent=agent,
        status=1,
        matcher=matcher,
        intent_manager=intent_manager,
        chain_id=chain_id,
    )

    typehash = keccak(text=ASSIGNMENT_TYPEHASH_DEF)
    manual = keccak(
        b"".join(
            [
                typehash,
                _bytes32_hex(assignment_id),
                _bytes32_hex(intent_id),
                _bytes32_hex(bid_id),
                _addr32(agent),
                _u256(1),
                _addr32(matcher),
                _addr32(intent_manager),
                _u256(chain_id),
            ]
        )
    )
    assert d1 == manual


def test_validation_digest_manual_equivalence() -> None:
    intent_id = "0x" + "11" * 32
    assignment_id = "0x" + "aa" * 32
    subnet_id = "0x" + "00" * 31 + "01"
    agent = "0x9290085Cd66bD1A3C7D277EF7DBcbD2e98457b6f"
    result_hash = "0x" + "cc" * 32
    proof_hash = "0x" + "dd" * 32
    root_hash = "0x" + "ee" * 32
    root_height = 1
    intent_manager = "0xB7f8BC63BbcaD18155201308C8f3540b07f84F5e"
    chain_id = 31337

    d1 = validation_digest(
        intent_id=intent_id,
        assignment_id=assignment_id,
        subnet_id=subnet_id,
        agent=agent,
        result_hash=result_hash,
        proof_hash=proof_hash,
        root_height=root_height,
        root_hash=root_hash,
        intent_manager=intent_manager,
        chain_id=chain_id,
    )

    typehash = keccak(text=VALIDATION_TYPEHASH_DEF)
    manual = keccak(
        b"".join(
            [
                typehash,
                _bytes32_hex(intent_id),
                _bytes32_hex(assignment_id),
                _bytes32_hex(subnet_id),
                _addr32(agent),
                _bytes32_hex(result_hash),
                _bytes32_hex(proof_hash),
                _u256(root_height),
                _bytes32_hex(root_hash),
                _addr32(intent_manager),
                _u256(chain_id),
            ]
        )
    )
    assert d1 == manual


def test_validation_batch_digest_manual_equivalence() -> None:
    subnet_id = "0x" + "00" * 31 + "01"
    items_hash_ = "0x" + "11" * 32
    root_height = 1
    root_hash = "0x" + "22" * 32
    intent_manager = "0xB7f8BC63BbcaD18155201308C8f3540b07f84F5e"
    chain_id = 31337

    d1 = validation_batch_digest(
        subnet_id=subnet_id,
        items_hash_=items_hash_,
        root_height=root_height,
        root_hash=root_hash,
        intent_manager=intent_manager,
        chain_id=chain_id,
    )

    typehash = keccak(text=VALIDATION_BATCH_TYPEHASH_DEF)
    manual = keccak(
        b"".join(
            [
                typehash,
                _bytes32_hex(subnet_id),
                _bytes32_hex(items_hash_),
                _u256(root_height),
                _bytes32_hex(root_hash),
                _addr32(intent_manager),
                _u256(chain_id),
            ]
        )
    )
    assert d1 == manual


def test_direct_intent_digest_manual_equivalence() -> None:
    signer = PrivateKeySigner(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    intent_id = "0x" + "11" * 32
    subnet_id = "0x" + "00" * 31 + "01"
    target_agent = "0x9290085Cd66bD1A3C7D277EF7DBcbD2e98457b6f"
    intent_manager = "0xB7f8BC63BbcaD18155201308C8f3540b07f84F5e"
    chain_id = 31337

    ph = params_hash(b"pingraw", b"")
    d1 = direct_intent_digest(
        intent_id=intent_id,
        subnet_id=subnet_id,
        requester=signer.address,
        intent_type="test",
        params_hash_=ph,
        deadline=1822275330,
        payment_token="0x0000000000000000000000000000000000000000",
        amount=123,
        target_agent=target_agent,
        intent_manager=intent_manager,
        chain_id=chain_id,
    )

    typehash = keccak(text=DIRECT_INTENT_TYPEHASH_DEF)
    manual = keccak(
        b"".join(
            [
                typehash,
                _bytes32_hex(intent_id),
                _bytes32_hex(subnet_id),
                _addr32(signer.address),
                keccak(text="test"),
                ph,
                _u256(1822275330),
                _addr32("0x0000000000000000000000000000000000000000"),
                _u256(123),
                _addr32(target_agent),
                _addr32(intent_manager),
                _u256(chain_id),
            ]
        )
    )
    assert d1 == manual


def test_agent_connect_digest_manual_equivalence_and_signature_recovery() -> None:
    signer = PrivateKeySigner(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )

    nonce = b"\x11" * 32
    ts = 1730000000
    agent_id = 123

    d1 = agent_connect_digest(
        agent_address=signer.address,
        timestamp=ts,
        random_nonce=nonce,
        agent_id=agent_id,
    )

    typehash = keccak(text=AGENT_CONNECT_TYPEHASH_DEF)
    manual = keccak(
        b"".join(
            [
                typehash,
                _addr32(signer.address),
                _u256(ts),
                nonce,
                _u256(agent_id),
            ]
        )
    )
    assert d1 == manual

    sig = signer.sign_message_32(d1)
    assert recover_address(d1, sig).lower() == signer.address.lower()
