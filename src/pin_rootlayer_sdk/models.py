from __future__ import annotations

from typing import Annotated, Optional, Union

from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import AfterValidator, BeforeValidator

from .encoding import (
    normalize_address,
    normalize_bytes32_hex,
    parse_bytes,
    parse_bytes32,
    to_camel,
    uint256_to_decimal_str,
)


def _validate_bytes32_len(v: bytes) -> bytes:
    if len(v) != 32:
        raise ValueError("expected 32 bytes")
    return v


BytesData = Annotated[bytes, BeforeValidator(parse_bytes)]
Bytes32 = Annotated[bytes, BeforeValidator(parse_bytes32), AfterValidator(_validate_bytes32_len)]
Uint256Str = Annotated[str, BeforeValidator(uint256_to_decimal_str)]


def _validate_hash32_hex(v: str) -> str:
    return normalize_bytes32_hex(v)


Hash32Hex = Annotated[str, BeforeValidator(_validate_hash32_hex)]
Address = Annotated[str, BeforeValidator(normalize_address)]


class SDKModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        ser_json_bytes="base64",
        extra="ignore",
    )


class ChainConfig(SDKModel):
    chain_id: int
    intent_manager_address: Address

    def normalized(self) -> ChainConfig:
        if self.chain_id <= 0:
            raise ValueError("chain_id must be > 0")
        return self


class IntentParams(SDKModel):
    intent_raw: BytesData
    metadata: Optional[BytesData] = None


class SubmitIntentRequest(SDKModel):
    intent_id: Hash32Hex
    subnet_id: Hash32Hex
    requester: Optional[Address] = None
    settle_chain: str
    intent_type: str
    params: IntentParams
    tips_token: Address = "0x0000000000000000000000000000000000000000"
    tips: Uint256Str = "0"
    deadline: int
    signature: Optional[BytesData] = None
    budget_token: Address = "0x0000000000000000000000000000000000000000"
    budget: Uint256Str = "0"


class SubmitIntentResponse(SDKModel):
    ok: bool
    msg: str = ""
    intent_id: str
    params_hash: BytesData
    intent_expiration: int


class SubmitIntentBatchRequest(SDKModel):
    items: list[SubmitIntentRequest]
    batch_id: Optional[str] = None
    partial_ok: Optional[bool] = None
    treat_exists_as_ok: Optional[bool] = None


class SubmitIntentBatchResponse(SDKModel):
    results: list[SubmitIntentResponse]
    success: int
    failed: int
    msg: str = ""


class GetIntentsRequest(SDKModel):
    intent_id: Optional[str] = None
    subnet_id: Optional[str] = None
    status: Optional[str] = None
    requester: Optional[str] = None
    min_deadline: Optional[int] = None
    min_tips: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    order_by: Optional[str] = None
    order_dir: Optional[str] = None


class Intent(SDKModel):
    intent_id: str
    subnet_id: str
    requester: str
    settle_chain: str
    intent_type: str
    params: Optional[IntentParams] = None
    params_hash: Optional[BytesData] = None
    tips_token: Optional[str] = None
    tips: Optional[str] = None
    budget_token: Optional[str] = None
    budget: Optional[str] = None
    deadline: Optional[int] = None
    intent_expiration: Optional[int] = None
    status: Optional[Union[str, int]] = None
    created_at: Optional[int] = None
    signature: Optional[BytesData] = None
    pending_confirmed: Optional[bool] = None
    processing_confirmed: Optional[bool] = None
    validation_confirmed: Optional[bool] = None


class GetIntentsResponse(SDKModel):
    intents: list[Intent]
    total: int
    page: int
    page_size: int
    total_pages: int


class GetIntentRequest(SDKModel):
    intent_id: str


class Ack(SDKModel):
    ok: bool
    msg: str = ""
    tx_hash: Optional[str] = None


class Assignment(SDKModel):
    assignment_id: Hash32Hex
    intent_id: Hash32Hex
    agent_id: Address
    bid_id: Hash32Hex
    status: Union[int, str]
    matcher_id: Address
    signature: Optional[BytesData] = None


class AssignmentBatch(SDKModel):
    assignments: list[Assignment]
    batch_id: Optional[str] = None
    created_at: Optional[int] = None


class DirectResult(SDKModel):
    intent_id: str
    agent_address: str
    success: bool
    result_data: BytesData
    result_hash: str
    error_message: str = ""
    timestamp: int
    target_agent_id: Optional[Uint256Str] = None
    subnet_id: Optional[Hash32Hex] = None


class SubmitDirectIntentRequest(SDKModel):
    intent_id: Hash32Hex
    subnet_id: Hash32Hex
    requester: Optional[Address] = None
    settle_chain: str
    intent_type: str
    params: IntentParams
    payment_token: Address = "0x0000000000000000000000000000000000000000"
    amount: Uint256Str
    deadline: int
    signature: Optional[BytesData] = None
    target_agent: Address
    target_agent_id: Uint256Str


class SubmitDirectIntentResponse(SDKModel):
    ok: bool
    msg: str = ""
    intent_id: str
    result: Optional[DirectResult] = None
    params_hash: Optional[BytesData] = None
    status: Optional[str] = None


class HealthCheckResponse(SDKModel):
    status: str
    service: str
    timestamp: int
    version: Optional[str] = None
    details: Optional[dict[str, str]] = None
