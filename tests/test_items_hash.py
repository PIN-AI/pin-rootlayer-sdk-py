from __future__ import annotations

from eth_utils import keccak, to_bytes

from pin_rootlayer_sdk.signing import ValidationItem, items_hash


def _u256(x: int) -> bytes:
    return x.to_bytes(32, "big")


def _bytes32_hex(h: str) -> bytes:
    assert h.startswith("0x") and len(h) == 66
    return bytes.fromhex(h[2:])


def _addr32(addr: str) -> bytes:
    b = to_bytes(hexstr=addr)
    assert len(b) == 20
    return b.rjust(32, b"\x00")


def test_items_hash_matches_manual_abi_encode() -> None:
    its = [
        ValidationItem(
            intent_id="0x" + "11" * 32,
            assignment_id="0x" + "aa" * 32,
            agent="0x9290085Cd66bD1A3C7D277EF7DBcbD2e98457b6f",
            result_hash="0x" + "cc" * 32,
            proof_hash="0x" + "dd" * 32,
        ),
        ValidationItem(
            intent_id="0x" + "22" * 32,
            assignment_id="0x" + "bb" * 32,
            agent="0xF39fd6e51aad88F6F4ce6aB8827279cffFb92266",
            result_hash="0x" + "ee" * 32,
            proof_hash="0x" + "ff" * 32,
        ),
    ]

    h1 = items_hash(its)

    # manual ABI encoding for a single argument of type (bytes32,bytes32,address,bytes32,bytes32)[]
    # abi.encode(items) = offset(0x20) || len || items...
    head = _u256(32)
    tail = _u256(len(its))
    for it in its:
        tail += _bytes32_hex(it.intent_id)  # type: ignore[arg-type]
        tail += _bytes32_hex(it.assignment_id)  # type: ignore[arg-type]
        tail += _addr32(it.agent)
        tail += _bytes32_hex(it.result_hash)  # type: ignore[arg-type]
        tail += _bytes32_hex(it.proof_hash)  # type: ignore[arg-type]

    manual = keccak(head + tail)
    assert h1 == manual
