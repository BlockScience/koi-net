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

# CLIENT ERRORS
class ClientError(RequestError):
    """Raised when this node makes an invalid request."""
    pass

class SelfRequestError(ClientError):
    """Raised when this node tries to request itself."""
    pass

class PartialNodeQueryError(ClientError):
    """Raised when this node attempts to query a partial node."""
    pass

class NodeNotFoundError(ClientError):
    """Raised when this node cannot find a node's URL."""
    pass

class TransportError(RequestError):
    """Raised when a transport error occurs during a request."""
    pass

# SERVER ERRORS
class ServerError(RequestError):
    """Raised when an server error occurs during a request."""
    pass

# PROTOCOL ERRORS
class RemoteProtocolError(ServerError):
    """Base for protocol response errors."""
    pass

class RemoteUnknownNodeError(RemoteProtocolError):
    """Raised when peer node is unknown."""
    pass
    
class RemoteInvalidKeyError(RemoteProtocolError):
    """Raised when peer node's public key doesn't match their RID."""
    pass
    
class RemoteInvalidSignatureError(RemoteProtocolError):
    """Raised when peer node's envelope signature is invalid."""
    pass

class RemoteInvalidTargetError(RemoteProtocolError):
    """Raised when peer node's target is not this node."""
    pass


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