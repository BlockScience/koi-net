import structlog
from rid_lib.types.koi_net_node import KoiNetNode
from .config import NodeConfig
from .protocol.node import NodeProfile

log = structlog.stdlib.get_logger()

    
class NodeIdentity:
    """Represents a node's identity (RID, profile)."""
    
    config: NodeConfig    
    
    def __init__(self, config: NodeConfig):
        self.config = config
        
    @property
    def rid(self) -> KoiNetNode:
        return self.config.koi_net.node_rid
    
    @property
    def profile(self) -> NodeProfile:
        return self.config.koi_net.node_profile