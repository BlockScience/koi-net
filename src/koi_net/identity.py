import logging
from pydantic import BaseModel
from rid_lib.ext.bundle import Bundle
from rid_lib.ext.cache import Cache
from rid_lib.types.koi_net_node import KoiNetNode
from .protocol.node import NodeProfile

logger = logging.getLogger(__name__)


class NodeIdentityModel(BaseModel):
    rid: KoiNetNode
    profile: NodeProfile
    
class NodeIdentity:
    """Represents a node's identity (RID, profile, bundle)."""
    
    _identity: NodeIdentityModel
    file_path: str
    cache: Cache
    
    def __init__(
        self,  
        name: str,
        profile: NodeProfile,
        cache: Cache,
        file_path: str = "identity.json"
    ):
        """Initializes node identity from a name and profile.
        
        Attempts to read identity from storage. If it doesn't already exist, a new RID is generated from the provided name, and that RID and profile are written to storage. Changes to the name or profile will update the stored identity.
        
        WARNING: If the name is changed, the RID will be overwritten which will have consequences for the rest of the network.
        """
        self.cache = cache
        self.file_path = file_path
        
        self._identity = None
        try:
            with open(file_path, "r") as f:
                self._identity = NodeIdentityModel.model_validate_json(f.read())
                    
        except FileNotFoundError:
            pass
        
        if self._identity:
            if self._identity.rid.name != name:
                logger.warning("Node name changed which will change this node's RID, if you really want to do this manually delete the identity JSON file")
            if self._identity.profile != profile:
                self._identity.profile = profile
        else:
            self._identity = NodeIdentityModel( 
                rid=KoiNetNode.generate(name), 
                profile=profile,
            )
                    
        with open(file_path, "w") as f:
            f.write(self._identity.model_dump_json(indent=2))
        
    @property
    def rid(self) -> KoiNetNode:
        return self._identity.rid
    
    @property
    def profile(self) -> NodeProfile:
        return self._identity.profile    
    
    @property
    def bundle(self) -> Bundle:
        return self.cache.read(self.rid)