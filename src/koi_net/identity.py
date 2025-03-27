from rid_lib.core import RIDType
from rid_lib.ext.bundle import Bundle
from rid_lib.ext.cache import Cache
from rid_lib.types.koi_net_edge import KoiNetEdge
from rid_lib.types.koi_net_node import KoiNetNode
from koi_net.protocol import NodeModel
from koi_net.protocol.node import NodeProvides, NodeType


class NodeIdentity:
    rid: KoiNetNode
    profile: NodeModel
    cache: Cache
    implicitly_provides: NodeProvides
        
    def __init__(self, rid: KoiNetNode, profile: NodeModel, cache: Cache):
        self.rid = rid
        self.profile = profile
        self.cache = cache
        
        koi_net_types = [KoiNetNode, KoiNetEdge]
        
        if profile.node_type == NodeType.PARTIAL:
            self.implicitly_provides = NodeProvides(
                event=koi_net_types
            )
        elif profile.node_type == NodeType.FULL:
            self.implicitly_provides = NodeProvides(
                state=koi_net_types,
                event=koi_net_types
            )
            
    @property
    def bundle(self) -> Bundle:
        return self.cache.read(self.rid)