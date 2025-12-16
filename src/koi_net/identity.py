from rid_lib.types import KoiNetNode
from .config.base import BaseNodeConfig
from .protocol.node import NodeProfile


class NodeIdentity:
    """Represents a node's identity (RID, profile)."""
    
    config: BaseNodeConfig
    
    def __init__(self, config: BaseNodeConfig):
        self.config = config
        
    @property
    def rid(self) -> KoiNetNode:
        return self.config.koi_net.node_rid
    
    @property
    def profile(self) -> NodeProfile:
        return self.config.koi_net.node_profile
