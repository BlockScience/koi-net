from pydantic import BaseModel
from .base import BaseNodeConfig, KoiNetConfig as BaseKoiNetConfig
from ..protocol.node import (
    NodeProfile as BaseNodeProfile, 
    NodeType, 
    NodeProvides
)


class NodeProfile(BaseNodeProfile):
    """Node profile config class for partial nodes."""
    base_url: str | None = None
    node_type: NodeType = NodeType.PARTIAL

class KoiNetConfig(BaseKoiNetConfig):
    """KOI-net config class for partial nodes."""
    node_profile: NodeProfile

class PollerConfig(BaseModel):
    """Poller config for partial nodes."""
    polling_interval: int = 5

class PartialNodeConfig(BaseNodeConfig):
    """Node config class for partial nodes."""
    koi_net: KoiNetConfig
    poller: PollerConfig = PollerConfig()