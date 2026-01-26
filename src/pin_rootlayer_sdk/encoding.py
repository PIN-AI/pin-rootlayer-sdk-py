from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from eth_utils import (  # type: ignore[attr-defined]
    is_checksum_address,
    is_hex,
    keccak,
    to_bytes,
    to_checksum_address,
)
from hexbytes import HexBytes

from .exceptions import SigningError


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def ensure_0x(s: str) -> str:
    s = s.strip()
    if s.startswith("0x") or s.startswith("0X"):
        return "0x" + s[2:]
    return "0x" + s


def normalize_address(addr: str) -> str:
    addr = ensure_0x(addr.strip())
    if addr == "0x":
        return "0x0000000000000000000000000000000000000000"
    try:
        return to_checksum_address(addr)
    except Exception as e:  # noqa: BLE001
        raise SigningError(f"invalid address: {addr}") from e


def normalize_bytes32_hex(v: str) -> str:
    v = ensure_0x(v.strip()).lower()
    if len(v) != 66:
        raise SigningError(f"expected 32-byte hex string, got length={len(v)}: {v}")
    if not is_hex(v):
        raise SigningError(f"invalid hex string: {v}")
    return v


def parse_bytes(value: Any) -> bytes:
    if value is None:
        return b""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, HexBytes):
        return bytes(value)
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("0x") or s.startswith("0X"):
            try:
                return bytes.fromhex(s[2:])
            except ValueError as e:
                raise SigningError(f"invalid 0x hex bytes: {value}") from e
        try:
            return base64.b64decode(s, validate=True)
        except binascii.Error as e:
            raise SigningError(f"invalid base64 bytes: {value}") from e
    raise SigningError(f"unsupported bytes type: {type(value)}")


def parse_bytes32(value: Any) -> bytes:
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("0x") or s.startswith("0X"):
            try:
                b = bytes.fromhex(s[2:])
            except ValueError as e:
                raise SigningError(f"invalid 0x hex bytes32: {value}") from e
        else:
            b = parse_bytes(s)
    else:
        b = parse_bytes(value)
    if len(b) != 32:
        raise SigningError(f"expected 32 bytes, got {len(b)}")
    return b


def bytes_to_hex(b: bytes) -> str:
    return "0x" + b.hex()


def bytes_to_b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def parse_uint256(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        raise SigningError("uint256 cannot be bool")
    if isinstance(value, int):
        if value < 0:
            raise SigningError("uint256 cannot be negative")
        return value
    if isinstance(value, Decimal):
        i = int(value)
        if Decimal(i) != value:
            raise SigningError("uint256 must be an integer")
        return parse_uint256(i)
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("0x") or s.startswith("0X"):
            return int(s, 16)
        return int(s, 10)
    raise SigningError(f"unsupported uint256 type: {type(value)}")


def uint256_to_decimal_str(value: Any) -> str:
    return str(parse_uint256(value))


def keccak256(*chunks: bytes) -> bytes:
    return keccak(b"".join(chunks))


def keccak_text(text: str) -> bytes:
    return keccak(text=text)


def as_abi_bytes32(v: Any) -> bytes:
    return parse_bytes32(v)


def as_abi_address(v: str) -> str:
    # eth_abi accepts checksum or lower-case 0x string
    return normalize_address(v)


def as_abi_uint256(v: Any) -> int:
    return parse_uint256(v)


def left_pad_32(b: bytes) -> bytes:
    if len(b) > 32:
        raise SigningError(f"cannot left-pad >32 bytes (got {len(b)})")
    return b.rjust(32, b"\x00")


def uint_to_32(value: int) -> bytes:
    if value < 0:
        raise SigningError("uint cannot be negative")
    return value.to_bytes(32, "big")


def address_to_32(addr: str) -> bytes:
    a = normalize_address(addr)
    raw = to_bytes(hexstr=a)
    if len(raw) != 20:
        raise SigningError("address must be 20 bytes")
    return left_pad_32(raw)


def bytes32_to_32(v: Any) -> bytes:
    b = parse_bytes32(v)
    return b


def enum_to_int(v: Any) -> int:
    if isinstance(v, int):
        return v
    try:
        val = v.value
    except AttributeError:
        val = None
    if isinstance(val, int):
        return int(val)
    raise SigningError(f"expected int enum, got {type(v)}")


@dataclass(frozen=True)
class ChainConfigInternal:
    chain_id: int
    intent_manager_address: str

    def normalized(self) -> ChainConfigInternal:
        if self.chain_id <= 0:
            raise SigningError("chain_id must be > 0")
        addr = normalize_address(self.intent_manager_address)
        return ChainConfigInternal(chain_id=int(self.chain_id), intent_manager_address=addr)


def normalize_chain_map(
    chains: Mapping[str, ChainConfigInternal] | None,
) -> dict[str, ChainConfigInternal]:
    if not chains:
        return {}
    out: dict[str, ChainConfigInternal] = {}
    for k, v in chains.items():
        out[k.strip().lower()] = v.normalized()
    return out


def remove_none(d: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    keys = [k for k, v in d.items() if v is None]
    for k in keys:
        d.pop(k, None)
    return d


def deep_remove_none(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: deep_remove_none(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [deep_remove_none(v) for v in obj if v is not None]
    return obj


def validate_checksum_address(addr: str) -> str:
    addr = ensure_0x(addr)
    if not is_checksum_address(addr):
        # still accept non-checksum, normalize to checksum
        return normalize_address(addr)
    return addr
