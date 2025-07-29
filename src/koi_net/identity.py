import logging
from rid_lib.ext.bundle import Bundle
from rid_lib.ext.cache import Cache
from rid_lib.types.koi_net_node import KoiNetNode
from .config import NodeConfig
from .protocol.node import NodeProfile
from .protocol.secure import PrivateKey


logger = logging.getLogger(__name__)

    
class NodeIdentity:
    """Represents a node's identity (RID, profile, bundle)."""
    
    config: NodeConfig    
    cache: Cache
    _priv_key: PrivateKey | None
    
    def __init__(
        self,
        config: NodeConfig,
        cache: Cache
    ):
        """Initializes node identity from a name and profile.
        
        Attempts to read identity from storage. If it doesn't already exist, a new RID is generated from the provided name, and that RID and profile are written to storage. Changes to the name or profile will update the stored identity.
        
        WARNING: If the name is changed, the RID will be overwritten which will have consequences for the rest of the network.
        """
        self.config = config
        self.cache = cache
        self._priv_key = None    
        
    @property
    def rid(self) -> KoiNetNode:
        return self.config.koi_net.node_rid
    
    @property
    def profile(self) -> NodeProfile:
        return self.config.koi_net.node_profile
    
    @property
    def bundle(self) -> Bundle:
        # NOTE: this could be a good place to use effector, lazy dereference -> create bundle and write to cache if it doesn't exist yet
        return self.cache.read(self.rid)
    
    @property
    def priv_key(self) -> PrivateKey:
        if not self._priv_key:
            with open(self.config.koi_net.private_key_pem_path, "r") as f:
                priv_key_pem = f.read()
                self._priv_key = PrivateKey.from_pem(priv_key_pem, self.config.env.priv_key_password)
        return self._priv_key