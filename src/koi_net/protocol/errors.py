from enum import StrEnum


class ErrorType(StrEnum):
    UnknownNode = "unknown_node"
    InvalidKey = "invalid_key"
    InvalidSignature = "invalid_signature"
    InvalidTarget = "invalid_target"

class ProtocolError(Exception):
    error_type: ErrorType
    
class UnknownNodeError(ProtocolError):
    error_type = ErrorType.UnknownNode
    
class InvalidKeyError(ProtocolError):
    error_type = ErrorType.InvalidKey
    
class InvalidSignatureError(ProtocolError):
    error_type = ErrorType.InvalidSignature

class InvalidTargetError(ProtocolError):
    error_type = ErrorType.InvalidTarget