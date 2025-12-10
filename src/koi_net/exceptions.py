# BASE EXCEPTION
class KoiNetError(Exception):
    """Base exception."""
    pass

# BUILD ERRORS
class BuildError(KoiNetError):
    """Raised when errors occur in build process."""
    pass

# NETWORK REQUEST ERRORS
class RequestError(KoiNetError):
    """Base for network request errors."""
    pass

class SelfRequestError(RequestError):
    """Raised when a node tries to request itself."""
    pass

class PartialNodeQueryError(RequestError):
    """Raised when attempting to query a partial node."""
    pass

class NodeNotFoundError(RequestError):
    """Raised when a node URL cannot be found."""
    pass

# PROTOCOL RESPONSE ERRORS
class ProtocolError(KoiNetError):
    """Base for protocol response errors."""
    pass

class UnknownNodeError(ProtocolError):
    """Raised when peer node is unknown."""
    pass
    
class InvalidKeyError(ProtocolError):
    """Raised when peer node's public key doesn't match their RID."""
    pass
    
class InvalidSignatureError(ProtocolError):
    """Raised when peer node's envelope signature is invalid."""
    pass

class InvalidTargetError(ProtocolError):
    """Raised when peer node's target is not this node."""
    pass