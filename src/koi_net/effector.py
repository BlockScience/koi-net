import logging
from typing import Callable
from rid_lib.ext import Cache, Bundle
from rid_lib.core import RID, RIDType

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .network.resolver import NetworkResolver
    from .processor.interface import ProcessorInterface
    from .context import ActionContext

logger = logging.getLogger(__name__)


class Effector:
    cache: Cache
    resolver: "NetworkResolver | None"
    processor: "ProcessorInterface | None"
    action_context: "ActionContext | None"
    _action_table: dict[
        type[RID], 
        Callable[
            ["ActionContext", RID], 
            Bundle | None
        ]
    ] = dict()
    
    def __init__(
        self, 
        cache: Cache,
    ):
        self.cache = cache
        self.resolver = None
        self.processor = None
        self.action_context = None
        self._action_table = self.__class__._action_table.copy()
        
    def set_processor(self, processor: "ProcessorInterface"):
        self.processor = processor
        
    def set_resolver(self, resolver: "NetworkResolver"):
        self.resolver = resolver
        
    def set_action_context(self, action_context: "ActionContext"):
        self.action_context = action_context
        
    @classmethod
    def register_default_action(cls, rid_type: RIDType):
        def decorator(func: Callable) -> Callable:
            cls._action_table[rid_type] = func
            return func
        return decorator
        
    def register_action(self, rid_type: RIDType):
        def decorator(func: Callable) -> Callable:
            self._action_table[rid_type] = func
            return func
        return decorator
    
    def _try_cache(self, rid: RID) -> Bundle | None:
        bundle = self.cache.read(rid)
        
        if bundle:
            logger.debug("Cache hit")
        else:
            logger.debug("Cache miss")
            
        return bundle
        
    def _try_action(self, rid: RID) -> Bundle | None:
        if type(rid) not in self._action_table:
            logger.debug("No action found")
            return
        
        logger.debug("Action found")
        func = self._action_table[type(rid)]
        bundle = func(
            ctx=self.action_context, 
            rid=rid
        )
        
        if bundle:
            logger.debug("Action hit")
        else:
            logger.debug("Action miss")
        
        return bundle

        
    def _try_network(self, rid: RID):
        bundle = self.resolver.fetch_remote_bundle(rid)
        
        if bundle:
            logger.debug("Network hit")
        else:
            logger.debug("Network miss")
        
        return bundle
    
    def deref(
        self, 
        rid: RID, 
        handle: bool = True
    ) -> Bundle | None:
        logger.debug(f"Dereferencing {rid}")
        
        bundle = (
            self._try_cache(rid) or
            self._try_action(rid) or
            self._try_network(rid)
        )
        
        if bundle and handle:
            self.processor.handle(bundle=bundle)
            # TODO: refactor for general solution, param to write through to cache before continuing
            # like `self.processor.kobj_queue.join()``
        
        return bundle