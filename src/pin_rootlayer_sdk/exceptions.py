from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RootLayerHTTPError(RuntimeError):
    status_code: int
    body: Any
    message: str = "RootLayer request failed"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.message} (status={self.status_code}) body={self.body!r}"


class ConfigurationError(ValueError):
    pass


class SigningError(ValueError):
    pass
