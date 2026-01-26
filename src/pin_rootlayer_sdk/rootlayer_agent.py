from __future__ import annotations

import secrets
import threading
import time
from typing import Any, Callable, Optional, cast

import grpc
from google.protobuf import empty_pb2

from ._proto.rootlayer import direct_pb2 as _direct_pb2
from .encoding import parse_uint256
from .signer import Signer
from .signing import agent_connect_digest

direct_pb2 = cast(Any, _direct_pb2)


def _normalize_agent_id(agent_id: int | str) -> str:
    agent_id_int = parse_uint256(agent_id)
    if agent_id_int >= 2**256:
        raise ValueError("agent_id exceeds uint256 range")
    return str(agent_id_int)


class AgentSession:
    def __init__(
        self,
        *,
        agent_address: str,
        agent_id: str,
        stream: Any,
        heartbeat_rpc: Callable[..., empty_pb2.Empty],
        submit_result_rpc: Callable[..., Any],
    ) -> None:
        self.agent_address = agent_address
        self.agent_id = agent_id
        self._stream = stream
        self._heartbeat_rpc = heartbeat_rpc
        self._submit_result_rpc = submit_result_rpc

        self._hb_stop: Optional[threading.Event] = None
        self._hb_thread: Optional[threading.Thread] = None

    def recv(self) -> Any:
        try:
            return next(self._stream)
        except StopIteration as e:
            raise EOFError("AgentConnect stream closed") from e

    def heartbeat(self, *, timeout: float | None = None) -> None:
        self._heartbeat_rpc(
            direct_pb2.HeartbeatRequest(
                agent_address=self.agent_address,
                timestamp=int(time.time()),
                agent_id=self.agent_id,
            ),
            timeout=timeout,
        )

    def submit_direct_result(
        self,
        req: Any,
        *,
        timeout: float | None = None,
    ) -> Any:
        return self._submit_result_rpc(req, timeout=timeout)

    def submit_direct_result_from_push(
        self,
        push: Any,
        *,
        result_data: bytes,
        success: bool,
        error_message: str = "",
        timeout: float | None = None,
    ) -> Any:
        return self.submit_direct_result(
            direct_pb2.DirectResultRequest(
                intent_id=push.intent_id,
                agent_address=self.agent_address,
                success=success,
                result_data=result_data,
                error_message=error_message,
                timestamp=int(time.time()),
                target_agent_id=push.target_agent_id,
                subnet_id=push.subnet_id,
            ),
            timeout=timeout,
        )

    def start_heartbeat(self, *, interval_s: float = 10.0, timeout: float | None = None) -> None:
        if interval_s <= 0:
            raise ValueError("interval_s must be > 0")
        if self._hb_thread is not None:
            return

        stop = threading.Event()
        self._hb_stop = stop

        def _run() -> None:
            while not stop.is_set():
                try:
                    self.heartbeat(timeout=timeout)
                except grpc.RpcError:
                    # Keep best-effort heartbeat; stream recv will surface hard failures.
                    pass
                stop.wait(interval_s)

        t = threading.Thread(
            target=_run,
            name=f"pin-rootlayer-heartbeat-{self.agent_id}",
            daemon=True,
        )
        self._hb_thread = t
        t.start()

    def stop_heartbeat(self, *, join_timeout_s: float = 2.0) -> None:
        if self._hb_stop is not None:
            self._hb_stop.set()
        if self._hb_thread is not None:
            self._hb_thread.join(timeout=join_timeout_s)
        self._hb_stop = None
        self._hb_thread = None

    def close(self) -> None:
        self.stop_heartbeat()
        cancel = getattr(self._stream, "cancel", None)
        if callable(cancel):
            cancel()


class RootLayerAgentClient:
    def __init__(
        self,
        grpc_target: str,
        *,
        signer: Signer,
        secure: bool = False,
        credentials: grpc.ChannelCredentials | None = None,
        options: Any | None = None,
    ) -> None:
        self._signer = signer
        if secure:
            creds = credentials or grpc.ssl_channel_credentials()
            self._channel = grpc.secure_channel(grpc_target, creds, options=options)
        else:
            self._channel = grpc.insecure_channel(grpc_target, options=options)

        self._agent_connect = self._channel.unary_stream(
            "/rootlayer.v1.RelayerService/AgentConnect",
            request_serializer=direct_pb2.AgentConnectRequest.SerializeToString,
            response_deserializer=direct_pb2.DirectIntentPush.FromString,
        )
        self._heartbeat = self._channel.unary_unary(
            "/rootlayer.v1.RelayerService/Heartbeat",
            request_serializer=direct_pb2.HeartbeatRequest.SerializeToString,
            response_deserializer=empty_pb2.Empty.FromString,
        )
        self._submit_direct_result = self._channel.unary_unary(
            "/rootlayer.v1.RelayerService/SubmitDirectResult",
            request_serializer=direct_pb2.DirectResultRequest.SerializeToString,
            response_deserializer=direct_pb2.DirectResultResponse.FromString,
        )

    def close(self) -> None:
        self._channel.close()

    def __enter__(self) -> RootLayerAgentClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:  # noqa: ANN401
        self.close()

    def agent_connect(
        self,
        *,
        agent_id: int | str,
        client_version: str = "pin-rootlayer-sdk-py",
        timeout: float | None = None,
    ) -> AgentSession:
        agent_id_norm = _normalize_agent_id(agent_id)
        ts = int(time.time())
        nonce = secrets.token_bytes(32)

        digest = agent_connect_digest(
            agent_address=self._signer.address,
            timestamp=ts,
            random_nonce=nonce,
            agent_id=agent_id_norm,
        )
        sig = self._signer.sign_message_32(digest)

        stream = self._agent_connect(
            direct_pb2.AgentConnectRequest(
                agent_address=self._signer.address,
                signature=sig,
                client_version=client_version,
                timestamp=ts,
                random_nonce=nonce,
                agent_id=agent_id_norm,
            ),
            timeout=timeout,
        )

        return AgentSession(
            agent_address=self._signer.address,
            agent_id=agent_id_norm,
            stream=stream,
            heartbeat_rpc=self._heartbeat,
            submit_result_rpc=self._submit_direct_result,
        )
