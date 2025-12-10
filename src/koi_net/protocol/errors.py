"""Defines KOI-net protocol errors."""

from enum import StrEnum
from ..exceptions import (
    ProtocolError,
    UnknownNodeError,
    InvalidKeyError,
    InvalidSignatureError,
    InvalidTargetError
)


class ErrorType(StrEnum):
    UnknownNode = "unknown_node"
    InvalidKey = "invalid_key"
    InvalidSignature = "invalid_signature"
    InvalidTarget = "invalid_target"

EXCEPTION_TO_ERROR_TYPE: dict[ProtocolError, ErrorType] = {
    UnknownNodeError: ErrorType.UnknownNode,
    InvalidKeyError: ErrorType.InvalidKey,
    InvalidSignatureError: ErrorType.InvalidSignature,
    InvalidTargetError: ErrorType.InvalidTarget
}