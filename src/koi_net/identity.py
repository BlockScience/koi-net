import logging
from rid_lib.ext.bundle import Bundle
from rid_lib.ext.cache import Cache
from rid_lib.types.koi_net_node import KoiNetNode

from .config import Config
from .protocol.node import NodeProfile

logger = logging.getLogger(__name__)

    
class NodeIdentity:
    """Represents a node's identity (RID, profile, bundle)."""
    
    config: Config    
    cache: Cache
    
    def __init__(
        self,
        config: Config,
        cache: Cache
    ):
        """Initializes node identity from a name and profile.
        
        Attempts to read identity from storage. If it doesn't already exist, a new RID is generated from the provided name, and that RID and profile are written to storage. Changes to the name or profile will update the stored identity.
        
        WARNING: If the name is changed, the RID will be overwritten which will have consequences for the rest of the network.
        """
        self.config = config
        self.cache = cache
        
    @property
    def rid(self) -> KoiNetNode:
        return self.config.koi_net.node_rid
    
    @property
    def profile(self) -> NodeProfile:
        return self.config.koi_net.node_profile 
    
    @property
    def bundle(self) -> Bundle:
        return self.cache.read(self.rid)