from enum import StrEnum


class ErrorTypes(StrEnum):
    UnknownNode = "unknown_node"
    InvalidKey = "invalid_key"
    InvalidSignature = "invalid_signature"
    InvalidTarget = "invalid_target"

class ProtocolError(Exception):
    error_type: ErrorTypes
    
class UnknownNodeError(ProtocolError):
    error_type = ErrorTypes.UnknownNode
    
class InvalidKeyError(ProtocolError):
    error_type = ErrorTypes.InvalidKey
    
class InvalidSignatureError(ProtocolError):
    error_type = ErrorTypes.InvalidSignature

class InvalidTargetError(ProtocolError):
    error_type = ErrorTypes.InvalidTarget