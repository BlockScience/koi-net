from typing import Callable
from koi_net.network_interface import NetworkInterface
from koi_net.processor.interface import ProcessorInterface
from rid_lib.ext import Cache, Bundle
from rid_lib.core import RID

class Effector:
    cache: Cache
    network: NetworkInterface
    processor: ProcessorInterface
    _action_table = dict[type[RID], Callable[[RID], Bundle | None]]
    
    def __init__(self, cache: Cache, network: NetworkInterface, processor: ProcessorInterface):
        self.cache = cache
        self.network = network
        self.processor = processor
    
    def deref(self, rid: RID, handle: bool = True) -> Bundle:
        bundle = self.cache.read(rid)
        
        if not bundle:
            # first check if there are any providers of this type in the network
            bundle = self.network.fetch_remote_bundle(rid)
        
        if not bundle:
            # be smart? if this node is a provider of the type, maybe hit action table first
            if type(rid) in self._action_table:
                bundle = self._action_table[type(rid)](rid)
        
        if not bundle:
            return None
        
        self.processor.handle(bundle=bundle)
        
        return bundle