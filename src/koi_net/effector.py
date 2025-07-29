import logging
from typing import Callable

from rid_lib.ext import Cache, Bundle
from rid_lib.core import RID, RIDType

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .network.interface import NetworkInterface
    from .processor.interface import ProcessorInterface

logger = logging.getLogger(__name__)


class Effector:
    cache: Cache
    network: "NetworkInterface | None"
    processor: "ProcessorInterface | None"
    _action_table: dict[type[RID], Callable[[RID], Bundle | None]]
    
    def __init__(
        self, 
        cache: Cache
    ):
        self.cache = cache
        self.network = None
        self.processor = None
        self._action_table = dict()
        
    def set_processor(self, processor: "ProcessorInterface"):
        self.processor = processor
        
    def set_network(self, network: "NetworkInterface"):
        self.network = network
        
    def register_action(self, rid_type: RIDType):
        def decorator(func: Callable) -> Callable:
            self._action_table[rid_type] = func
            return func
        return decorator
    
    def deref(self, rid: RID, handle: bool = True) -> Bundle | None:
        logger.debug(f"Dereferencing {rid}")
        bundle = self.cache.read(rid)
        
        if bundle:
            logger.debug("Cache hit")
        else:
            logger.debug("Cache miss")
            
            # be smart? if this node is a provider of the type, maybe hit action table first
            if type(rid) in self._action_table:
                logger.debug("Action found")
                bundle = self._action_table[type(rid)](rid)
            else:
                logger.debug("No action found")
        
            if bundle:
                logger.debug("Action hit")
            else:
                logger.debug("Action miss")
            
                # first check if there are any providers of this type in the network
                bundle = self.network.fetch_remote_bundle(rid)
            
                if bundle:
                    logger.debug("Network hit")
                else:
                    logger.debug("Network miss")
                    return
            
        self.processor.handle(bundle=bundle)
        
        return bundle