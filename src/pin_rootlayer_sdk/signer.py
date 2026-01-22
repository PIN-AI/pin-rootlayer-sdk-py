from __future__ import annotations

from typing import Protocol, runtime_checkable

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address

from .exceptions import SigningError


@runtime_checkable
class Signer(Protocol):
    @property
    def address(self) -> str:  # EIP-55
        ...

    def sign_message_32(self, digest32: bytes) -> bytes:
        """Sign 32-byte digest using EIP-191 (ethers.signMessage(getBytes(digest)))."""


class EthAccountSigner:
    def __init__(self, private_key: str | bytes):
        try:
            self._acct = Account.from_key(private_key)
        except Exception as e:  # noqa: BLE001
            raise SigningError("invalid private key") from e

    @property
    def address(self) -> str:
        return to_checksum_address(self._acct.address)

    def sign_message_32(self, digest32: bytes) -> bytes:
        if len(digest32) != 32:
            raise SigningError("digest32 must be 32 bytes")
        msg = encode_defunct(primitive=digest32)
        sig = self._acct.sign_message(msg).signature
        if len(sig) != 65:
            raise SigningError("signature must be 65 bytes")
        return bytes(sig)


class PrivateKeySigner(EthAccountSigner):
    pass
