import structlog
from typing import Callable
from enum import StrEnum
from rid_lib.ext import Cache, Bundle
from rid_lib.core import RID, RIDType
from rid_lib.types import KoiNetNode
from .network.resolver import NetworkResolver
from .processor.kobj_queue import KobjQueue
from .identity import NodeIdentity

log = structlog.stdlib.get_logger()


class ActionContext:
    """Provides action handlers access to other subsystems."""
    
    identity: NodeIdentity

    def __init__(
        self,
        identity: NodeIdentity,
    ):
        self.identity = identity
    

class BundleSource(StrEnum):
    CACHE = "CACHE"
    ACTION = "ACTION"

class Effector:
    """Subsystem for dereferencing RIDs."""
    
    cache: Cache
    resolver: NetworkResolver
    kobj_queue: KobjQueue | None
    action_context: ActionContext | None
    _action_table: dict[
        type[RID], 
        Callable[
            [ActionContext, RID], 
            Bundle | None
        ]
    ] = dict()
    
    def __init__(
        self, 
        cache: Cache,
        resolver: NetworkResolver,
        kobj_queue: KobjQueue,
        identity: NodeIdentity
    ):
        self.cache = cache
        self.resolver = resolver
        self.kobj_queue = kobj_queue
        self.action_context = ActionContext(identity)
        self._action_table = self.__class__._action_table.copy()
    
    @classmethod
    def register_default_action(cls, rid_type: RIDType):
        def decorator(func: Callable) -> Callable:
            cls._action_table[rid_type] = func
            return func
        return decorator
        
    def register_action(self, rid_type: RIDType):
        """Registers a new dereference action for an RID type.
        
        Example:
            This function should be used as a decorator on an action function::
            
                @node.register_action(KoiNetNode)
                def deref_koi_net_node(ctx: ActionContext, rid: KoiNetNode):
                    # return a Bundle or None
                    return
        """
        def decorator(func: Callable) -> Callable:
            self._action_table[rid_type] = func
            return func
        return decorator
    
    def _try_cache(self, rid: RID) -> tuple[Bundle, BundleSource] | None:
        bundle = self.cache.read(rid)
        
        if bundle:
            log.debug("Cache hit")
            return bundle, BundleSource.CACHE
        else:
            log.debug("Cache miss")
            return None
                    
    def _try_action(self, rid: RID) -> tuple[Bundle, BundleSource] | None:
        if type(rid) not in self._action_table:
            log.debug("No action available")
            return None
        
        log.debug("Action available")
        func = self._action_table[type(rid)]
        bundle = func(
            ctx=self.action_context, 
            rid=rid
        )
        
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
        handle_result: bool = True
    ) -> Bundle | None:
        """Dereferences an RID.
        
        Attempts to dereference an RID by (in order) reading the cache, 
        calling a bound action, or fetching from other nodes in the 
        newtork.
        
        Args:
            rid: RID to dereference
            refresh_cache: skips cache read when `True` 
            use_network: enables fetching from other nodes when `True`
            handle_result: handles resulting bundle with knowledge pipeline when `True`
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
            self.kobj_queue.put_kobj(
                bundle=bundle, 
                source=source if type(source) is KoiNetNode else None
            )

            # TODO: refactor for general solution, param to write through to cache before continuing
            # like `self.processor.kobj_queue.join()``

        return bundle