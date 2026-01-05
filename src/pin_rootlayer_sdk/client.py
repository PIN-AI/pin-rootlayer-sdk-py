from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .exceptions import ConfigurationError, RootLayerHTTPError
from .models import (
    Ack,
    Assignment,
    AssignmentBatch,
    ChainConfig,
    GetIntentsRequest,
    GetIntentsResponse,
    HealthCheckResponse,
    Intent,
    SubmitDirectIntentRequest,
    SubmitDirectIntentResponse,
    SubmitIntentBatchRequest,
    SubmitIntentBatchResponse,
    SubmitIntentRequest,
    SubmitIntentResponse,
)
from .signer import Signer
from .signing import direct_intent_digest, intent_digest, params_hash


class RootLayerClient:
    def __init__(
        self,
        rootlayer_url: str,
        *,
        signer: Signer | None = None,
        chains: Mapping[str, ChainConfig] | None = None,
        timeout: float = 30.0,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self._signer = signer
        self._chains = {k: v for k, v in (chains or {}).items()}
        normalized = {kk.strip().lower(): vv for kk, vv in self._chains.items()}
        self._chains_norm = {k: v.normalized() for k, v in normalized.items()}

        self._client = httpx.Client(
            base_url=rootlayer_url.rstrip("/"),
            timeout=timeout,
            headers=dict(headers or {}),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> RootLayerClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:  # noqa: ANN401
        self.close()

    def _chain_for(self, settle_chain: str) -> ChainConfig:
        key = settle_chain.strip().lower()
        cfg = self._chains_norm.get(key)
        if cfg is None:
            raise ConfigurationError(f"unknown settle_chain: {settle_chain}")
        return cfg

    def _require_signer(self) -> Signer:
        if self._signer is None:
            raise ConfigurationError("signer is required for auto-signing")
        return self._signer

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: Any | None = None,
    ) -> Any:
        try:
            resp = self._client.request(method, path, json=json_body, params=params)
        except httpx.HTTPError as e:
            raise RootLayerHTTPError(
                status_code=0,
                body=str(e),
                message="RootLayer request error",
            ) from e

        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:  # noqa: BLE001
                body = resp.text
            raise RootLayerHTTPError(status_code=resp.status_code, body=body)

        if resp.status_code == 204:
            return None

        try:
            return resp.json()
        except Exception:  # noqa: BLE001
            return resp.text

    def check(self) -> HealthCheckResponse:
        data = self._request_json("GET", "/health")
        return HealthCheckResponse.model_validate(data)

    def submit_intent(self, req: SubmitIntentRequest | Mapping[str, Any]) -> SubmitIntentResponse:
        req_model = (
            req if isinstance(req, SubmitIntentRequest) else SubmitIntentRequest.model_validate(req)
        )

        if req_model.signature is None:
            signer = self._require_signer()
            if req_model.requester is None:
                req_model.requester = signer.address  # type: ignore[misc]

            chain = self._chain_for(req_model.settle_chain)

            ph = params_hash(req_model.params.intent_raw, req_model.params.metadata or b"")
            digest = intent_digest(
                intent_id=req_model.intent_id,
                subnet_id=req_model.subnet_id,
                requester=req_model.requester,
                intent_type=req_model.intent_type,
                params_hash_=ph,
                deadline=int(req_model.deadline),
                budget_token=req_model.budget_token,
                budget=int(req_model.budget),
                intent_manager=chain.intent_manager_address,
                chain_id=chain.chain_id,
            )
            req_model.signature = signer.sign_message_32(digest)  # type: ignore[misc]

        body = req_model.model_dump(mode="json", by_alias=True, exclude_none=True)
        data = self._request_json("POST", "/api/v1/intents/submit", json_body=body)
        return SubmitIntentResponse.model_validate(data)

    def submit_intent_batch(
        self,
        req: SubmitIntentBatchRequest | Mapping[str, Any],
    ) -> SubmitIntentBatchResponse:
        req_model = (
            req
            if isinstance(req, SubmitIntentBatchRequest)
            else SubmitIntentBatchRequest.model_validate(req)
        )

        # auto-sign per item if possible
        if any(item.signature is None for item in req_model.items):
            signer = self._require_signer()
            for item in req_model.items:
                if item.signature is not None:
                    continue
                if item.requester is None:
                    item.requester = signer.address  # type: ignore[misc]
                chain = self._chain_for(item.settle_chain)
                ph = params_hash(item.params.intent_raw, item.params.metadata or b"")
                digest = intent_digest(
                    intent_id=item.intent_id,
                    subnet_id=item.subnet_id,
                    requester=item.requester,
                    intent_type=item.intent_type,
                    params_hash_=ph,
                    deadline=int(item.deadline),
                    budget_token=item.budget_token,
                    budget=int(item.budget),
                    intent_manager=chain.intent_manager_address,
                    chain_id=chain.chain_id,
                )
                item.signature = signer.sign_message_32(digest)  # type: ignore[misc]

        body = req_model.model_dump(mode="json", by_alias=True, exclude_none=True)
        data = self._request_json("POST", "/api/v1/intents/submit/batch", json_body=body)
        return SubmitIntentBatchResponse.model_validate(data)

    def get_intent(self, intent_id: str) -> Intent:
        data = self._request_json("GET", f"/api/v1/intents/query/{intent_id}")
        return Intent.model_validate(data)

    def get_intents(
        self,
        req: GetIntentsRequest | Mapping[str, Any] | None = None,
    ) -> GetIntentsResponse:
        req_model = GetIntentsRequest.model_validate(req or {})
        params = req_model.model_dump(by_alias=False, exclude_none=True)
        data = self._request_json("GET", "/api/v1/intents/query", params=params)
        return GetIntentsResponse.model_validate(data)

    def post_assignment(self, req: Assignment | Mapping[str, Any]) -> Ack:
        req_model = req if isinstance(req, Assignment) else Assignment.model_validate(req)
        body = req_model.model_dump(mode="json", by_alias=True, exclude_none=True)
        data = self._request_json(
            "POST",
            "/api/v1/callbacks/assignment/submit",
            json_body=body,
        )
        return Ack.model_validate(data)

    def post_assignment_batch(self, req: AssignmentBatch | Mapping[str, Any]) -> Ack:
        req_model = req if isinstance(req, AssignmentBatch) else AssignmentBatch.model_validate(req)
        body = req_model.model_dump(mode="json", by_alias=True, exclude_none=True)
        data = self._request_json(
            "POST",
            "/api/v1/callbacks/assignments/submit",
            json_body=body,
        )
        return Ack.model_validate(data)

    def submit_direct_intent(
        self, req: SubmitDirectIntentRequest | Mapping[str, Any]
    ) -> SubmitDirectIntentResponse:
        req_model = (
            req
            if isinstance(req, SubmitDirectIntentRequest)
            else SubmitDirectIntentRequest.model_validate(req)
        )

        if req_model.signature is None:
            signer = self._require_signer()
            if req_model.requester is None:
                req_model.requester = signer.address  # type: ignore[misc]
            chain = self._chain_for(req_model.settle_chain)
            ph = params_hash(req_model.params.intent_raw, req_model.params.metadata or b"")
            digest = direct_intent_digest(
                intent_id=req_model.intent_id,
                subnet_id=req_model.subnet_id,
                requester=req_model.requester,
                intent_type=req_model.intent_type,
                params_hash_=ph,
                deadline=int(req_model.deadline),
                payment_token=req_model.payment_token,
                amount=int(req_model.amount),
                target_agent=req_model.target_agent,
                intent_manager=chain.intent_manager_address,
                chain_id=chain.chain_id,
            )
            req_model.signature = signer.sign_message_32(digest)  # type: ignore[misc]

        body = req_model.model_dump(mode="json", by_alias=True, exclude_none=True)
        data = self._request_json("POST", "/v1/direct/intents", json_body=body)
        return SubmitDirectIntentResponse.model_validate(data)
