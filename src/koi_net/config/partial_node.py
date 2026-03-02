from ..protocol.node import NodeProfile, NodeType
from .base import BaseNodeConfig
from .poller_config import PollerConfig


class PartialNodeProfile(NodeProfile):
    """Node profile config class for partial nodes."""
    base_url: str | None = None
    node_type: NodeType = NodeType.PARTIAL

class PartialNodeConfig(BaseNodeConfig):
    """Node config class for partial nodes."""
    poller: PollerConfig = PollerConfig()