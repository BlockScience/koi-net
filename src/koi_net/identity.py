from rid_lib.ext.bundle import Bundle
from rid_lib.ext.cache import Cache
from rid_lib.types.koi_net_node import KoiNetNode
from .protocol.node import NodeProfile


class NodeIdentity:
    rid: KoiNetNode
    profile: NodeProfile
    cache: Cache
        
    def __init__(self, rid: KoiNetNode, profile: NodeProfile, cache: Cache):
        self.rid = rid
        self.profile = profile
        self.cache = cache
            
    @property
    def bundle(self) -> Bundle:
        return self.cache.read(self.rid)