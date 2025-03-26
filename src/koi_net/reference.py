from dataclasses import dataclass
from rid_lib.ext.bundle import Bundle
from rid_lib.ext.cache import Cache
from rid_lib.types.koi_net_node import KoiNetNode
from koi_net.protocol import NodeModel


@dataclass
class NodeReference:
    rid: KoiNetNode
    profile: NodeModel
    cache: Cache
    
    @property
    def bundle(self):
        return self.cache.read(self.rid)