from dataclasses import dataclass
from typing import Callable
from enum import StrEnum

import structlog
from rid_lib.ext import Cache, Bundle
from rid_lib.core import RID, RIDType
from rid_lib.types import KoiNetNode

from .processor.context import HandlerContext
from .network.resolver import NetworkResolver
from .processor.kobj_queue import KobjQueue

log = structlog.stdlib.get_logger()

@dataclass
class DerefHandler:
    func: Callable[[HandlerContext, RID], Bundle | None]
    rid_types: tuple[RIDType]
    
    def __call__(self, ctx: HandlerContext, rid: RID) -> Bundle | None:
        return self.func(ctx, rid)
    
    @classmethod
    def create(cls, rid_types: tuple[RIDType]):
        def decorator(func: Callable) -> DerefHandler:
            handler = cls(func, rid_types)
            return handler
        return decorator


class BundleSource(StrEnum):
    CACHE = "CACHE"
    ACTION = "ACTION"

class Effector:
    """Subsystem for dereferencing RIDs."""
    
    cache: Cache
    resolver: NetworkResolver
    kobj_queue: KobjQueue
    handler_context: HandlerContext
    
    def __init__(
        self, 
        cache: Cache,
        resolver: NetworkResolver,
        kobj_queue: KobjQueue,
        handler_context: HandlerContext,
        deref_handlers: list[DerefHandler]
    ):
        self.cache = cache
        self.resolver = resolver
        self.kobj_queue = kobj_queue
        self.handler_context = handler_context
        self.deref_handlers = deref_handlers
        
        self.handler_context.set_effector(self)
    
    def _try_cache(self, rid: RID) -> tuple[Bundle, BundleSource] | None:
        bundle = self.cache.read(rid)
        
        if bundle:
            log.debug("Cache hit")
            return bundle, BundleSource.CACHE
        else:
            log.debug("Cache miss")
            return None
            
    def _try_action(self, rid: RID) -> tuple[Bundle, BundleSource] | None:
        action = None
        for handler in self.deref_handlers:
            if type(rid) not in handler.rid_types:
                continue
            action = handler
            break
        
        if not action:
            log.debug("No action found")
            return None
        
        bundle = action(ctx=self.handler_context, rid=rid)
        
        if bundle:
            log.debug("Action hit")
            return bundle, BundleSource.ACTION
        else:
            log.debug("Action miss")
            return None
        
    def _try_network(self, rid: RID) -> tuple[Bundle, KoiNetNode] | None:
        bundle, source = self.resolver.fetch_remote_bundle(rid)
        
        if bundle:
            log.debug("Network hit")
            return bundle, source
        else:
            log.debug("Network miss")
            return None
        
    def deref(
        self, 
        rid: RID,
        refresh_cache: bool = False,
        use_network: bool = False,
        handle_result: bool = True,
        write_through: bool = False
    ) -> Bundle | None:
        """Dereferences an RID.
        
        Attempts to dereference an RID by (in order) reading the cache, 
        calling a bound action, or fetching from other nodes in the 
        newtork.
        
        Args:
            rid: RID to dereference
            refresh_cache: skips cache read when `True` 
            use_network: enables fetching from other nodes when `True`
            handle_result: sends resulting bundle to kobj queue when `True`
            write_through: waits for kobj queue to empty when `True`
        """
        
        log.debug(f"Dereferencing {rid!r}")
        
        bundle, source = (
            # if `refresh_cache`, skip try cache
            not refresh_cache and self._try_cache(rid) or 
            self._try_action(rid) or
            use_network and self._try_network(rid) or
            # if not found, bundle and source set to None
            (None, None) 
        )
        
        if (
            handle_result 
            and bundle is not None 
            and source != BundleSource.CACHE
        ):            
            self.kobj_queue.push(
                bundle=bundle, 
                source=source if type(source) is KoiNetNode else None
            )
            
            if write_through:
                self.kobj_queue.q.join()
                
        return bundle