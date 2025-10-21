from pydantic import BaseModel
from koi_net.config.core import NodeConfig, KoiNetConfig
from ..protocol.node import NodeProfile, NodeType, NodeProvides


class NodeProfile(NodeProfile):
    base_url: str | None = None
    node_type: NodeType = NodeType.PARTIAL

class KoiNetConfig(KoiNetConfig):
    node_profile: NodeProfile    

class PollerConfig(BaseModel):
    polling_interval: int = 5

class PartialNodeConfig(NodeConfig):
    koi_net: KoiNetConfig
    poller: PollerConfig = PollerConfig()