from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak, to_checksum_address

from .encoding import (
    as_abi_address,
    as_abi_bytes32,
    as_abi_uint256,
    keccak_text,
    parse_bytes,
    parse_bytes32,
)
from .exceptions import SigningError
from .signer import Signer

INTENT_TYPEHASH_DEF = (
    "PIN_INTENT_V1(bytes32,bytes32,address,bytes32,bytes32,uint256,address,uint256,address,uint256)"
)
ASSIGNMENT_TYPEHASH_DEF = (
    "PIN_ASSIGNMENT_V1(bytes32,bytes32,bytes32,address,uint8,address,address,uint256)"
)
VALIDATION_TYPEHASH_DEF = (
    "PIN_VALIDATION_V1(bytes32,bytes32,bytes32,address,bytes32,bytes32,uint64,bytes32,address,uint256)"
)
VALIDATION_BATCH_TYPEHASH_DEF = (
    "PIN_VALIDATION_BATCH_V1(bytes32,bytes32,uint64,bytes32,address,uint256)"
)
DIRECT_INTENT_TYPEHASH_DEF = (
    "PIN_DIRECT_INTENT_V1(bytes32,bytes32,address,bytes32,bytes32,uint256,address,uint256,address,address,uint256)"
)

INTENT_TYPEHASH = keccak_text(INTENT_TYPEHASH_DEF)
ASSIGNMENT_TYPEHASH = keccak_text(ASSIGNMENT_TYPEHASH_DEF)
VALIDATION_TYPEHASH = keccak_text(VALIDATION_TYPEHASH_DEF)
VALIDATION_BATCH_TYPEHASH = keccak_text(VALIDATION_BATCH_TYPEHASH_DEF)
DIRECT_INTENT_TYPEHASH = keccak_text(DIRECT_INTENT_TYPEHASH_DEF)


def params_hash(intent_raw: bytes | str, metadata: bytes | str = b"") -> bytes:
    raw = parse_bytes(intent_raw)
    meta = parse_bytes(metadata)
    if len(raw) == 0:
        raise SigningError("params.intent_raw cannot be empty")
    return keccak(raw + meta)


def recover_address(digest32: bytes, signature: bytes | str) -> str:
    d = parse_bytes32(digest32)
    sig = parse_bytes(signature)
    if len(sig) != 65:
        raise SigningError("signature must be 65 bytes")
    msg = encode_defunct(primitive=d)
    addr = Account.recover_message(msg, signature=sig)
    return to_checksum_address(addr)


def intent_digest(
    *,
    intent_id: bytes | str,
    subnet_id: bytes | str,
    requester: str,
    intent_type: str,
    params_hash_: bytes | str,
    deadline: int,
    budget_token: str,
    budget: int | str,
    intent_manager: str,
    chain_id: int,
) -> bytes:
    encoded = encode(
        [
            "bytes32",
            "bytes32",
            "bytes32",
            "address",
            "bytes32",
            "bytes32",
            "uint256",
            "address",
            "uint256",
            "address",
            "uint256",
        ],
        [
            as_abi_bytes32(INTENT_TYPEHASH),
            as_abi_bytes32(intent_id),
            as_abi_bytes32(subnet_id),
            as_abi_address(requester),
            as_abi_bytes32(keccak_text(intent_type)),
            as_abi_bytes32(params_hash_),
            as_abi_uint256(deadline),
            as_abi_address(budget_token),
            as_abi_uint256(budget),
            as_abi_address(intent_manager),
            as_abi_uint256(chain_id),
        ],
    )
    return keccak(encoded)


def sign_intent(signer: Signer, **kwargs: object) -> bytes:
    d = intent_digest(**kwargs)  # type: ignore[arg-type]
    return signer.sign_message_32(d)


def assignment_digest(
    *,
    assignment_id: bytes | str,
    intent_id: bytes | str,
    bid_id: bytes | str,
    agent: str,
    status: int,
    matcher: str,
    intent_manager: str,
    chain_id: int,
) -> bytes:
    encoded = encode(
        [
            "bytes32",
            "bytes32",
            "bytes32",
            "bytes32",
            "address",
            "uint8",
            "address",
            "address",
            "uint256",
        ],
        [
            as_abi_bytes32(ASSIGNMENT_TYPEHASH),
            as_abi_bytes32(assignment_id),
            as_abi_bytes32(intent_id),
            as_abi_bytes32(bid_id),
            as_abi_address(agent),
            int(status),
            as_abi_address(matcher),
            as_abi_address(intent_manager),
            as_abi_uint256(chain_id),
        ],
    )
    return keccak(encoded)


def sign_assignment(signer: Signer, **kwargs: object) -> bytes:
    d = assignment_digest(**kwargs)  # type: ignore[arg-type]
    return signer.sign_message_32(d)


def validation_digest(
    *,
    intent_id: bytes | str,
    assignment_id: bytes | str,
    subnet_id: bytes | str,
    agent: str,
    result_hash: bytes | str,
    proof_hash: bytes | str,
    root_height: int,
    root_hash: bytes | str,
    intent_manager: str,
    chain_id: int,
) -> bytes:
    encoded = encode(
        [
            "bytes32",
            "bytes32",
            "bytes32",
            "bytes32",
            "address",
            "bytes32",
            "bytes32",
            "uint64",
            "bytes32",
            "address",
            "uint256",
        ],
        [
            as_abi_bytes32(VALIDATION_TYPEHASH),
            as_abi_bytes32(intent_id),
            as_abi_bytes32(assignment_id),
            as_abi_bytes32(subnet_id),
            as_abi_address(agent),
            as_abi_bytes32(result_hash),
            as_abi_bytes32(proof_hash),
            int(root_height),
            as_abi_bytes32(root_hash),
            as_abi_address(intent_manager),
            as_abi_uint256(chain_id),
        ],
    )
    return keccak(encoded)


def sign_validation(signer: Signer, **kwargs: object) -> bytes:
    d = validation_digest(**kwargs)  # type: ignore[arg-type]
    return signer.sign_message_32(d)


@dataclass(frozen=True)
class ValidationItem:
    intent_id: bytes | str
    assignment_id: bytes | str
    agent: str
    result_hash: bytes | str
    proof_hash: bytes | str


def items_hash(items: Sequence[ValidationItem]) -> bytes:
    if len(items) == 0:
        raise SigningError("items must not be empty")
    tuples = [
        (
            as_abi_bytes32(it.intent_id),
            as_abi_bytes32(it.assignment_id),
            as_abi_address(it.agent),
            as_abi_bytes32(it.result_hash),
            as_abi_bytes32(it.proof_hash),
        )
        for it in items
    ]
    encoded = encode(["(bytes32,bytes32,address,bytes32,bytes32)[]"], [tuples])
    return keccak(encoded)


def validation_batch_digest(
    *,
    subnet_id: bytes | str,
    items_hash_: bytes | str,
    root_height: int,
    root_hash: bytes | str,
    intent_manager: str,
    chain_id: int,
) -> bytes:
    encoded = encode(
        [
            "bytes32",
            "bytes32",
            "bytes32",
            "uint64",
            "bytes32",
            "address",
            "uint256",
        ],
        [
            as_abi_bytes32(VALIDATION_BATCH_TYPEHASH),
            as_abi_bytes32(subnet_id),
            as_abi_bytes32(items_hash_),
            int(root_height),
            as_abi_bytes32(root_hash),
            as_abi_address(intent_manager),
            as_abi_uint256(chain_id),
        ],
    )
    return keccak(encoded)


def sign_validation_batch(signer: Signer, **kwargs: object) -> bytes:
    d = validation_batch_digest(**kwargs)  # type: ignore[arg-type]
    return signer.sign_message_32(d)


def direct_intent_digest(
    *,
    intent_id: bytes | str,
    subnet_id: bytes | str,
    requester: str,
    intent_type: str,
    params_hash_: bytes | str,
    deadline: int,
    payment_token: str,
    amount: int | str,
    target_agent: str,
    intent_manager: str,
    chain_id: int,
) -> bytes:
    encoded = encode(
        [
            "bytes32",
            "bytes32",
            "bytes32",
            "address",
            "bytes32",
            "bytes32",
            "uint256",
            "address",
            "uint256",
            "address",
            "address",
            "uint256",
        ],
        [
            as_abi_bytes32(DIRECT_INTENT_TYPEHASH),
            as_abi_bytes32(intent_id),
            as_abi_bytes32(subnet_id),
            as_abi_address(requester),
            as_abi_bytes32(keccak_text(intent_type)),
            as_abi_bytes32(params_hash_),
            as_abi_uint256(deadline),
            as_abi_address(payment_token),
            as_abi_uint256(amount),
            as_abi_address(target_agent),
            as_abi_address(intent_manager),
            as_abi_uint256(chain_id),
        ],
    )
    return keccak(encoded)


def sign_direct_intent(signer: Signer, **kwargs: object) -> bytes:
    d = direct_intent_digest(**kwargs)  # type: ignore[arg-type]
    return signer.sign_message_32(d)



