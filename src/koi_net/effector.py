import logging
from typing import Callable
from enum import StrEnum
from rid_lib.ext import Cache, Bundle
from rid_lib.core import RID, RIDType
from rid_lib.types import KoiNetNode

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .network.resolver import NetworkResolver
    from .processor.interface import ProcessorInterface
    from .context import ActionContext

logger = logging.getLogger(__name__)


class BundleSource(StrEnum):
    CACHE = "CACHE"
    ACTION = "ACTION"

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
    
    def _try_cache(self, rid: RID) -> tuple[Bundle, BundleSource] | None:
        bundle = self.cache.read(rid)
        
        if bundle:
            logger.debug("Cache hit")
            return bundle, BundleSource.CACHE
        else:
            logger.debug("Cache miss")
            return None
                    
    def _try_action(self, rid: RID) -> tuple[Bundle, BundleSource] | None:
        if type(rid) not in self._action_table:
            logger.debug("No action available")
            return None
        
        logger.debug("Action available")
        func = self._action_table[type(rid)]
        bundle = func(
            ctx=self.action_context, 
            rid=rid
        )
        
        if bundle:
            logger.debug("Action hit")
            return bundle, BundleSource.ACTION
        else:
            logger.debug("Action miss")
            return None

        
    def _try_network(self, rid: RID) -> tuple[Bundle, KoiNetNode] | None:
        bundle, source = self.resolver.fetch_remote_bundle(rid)
        
        if bundle:
            logger.debug("Network hit")
            return bundle, source
        else:
            logger.debug("Network miss")
            return None
        
    
    def deref(
        self, 
        rid: RID,
        refresh_cache: bool = False,
        use_network: bool = False,
        handle_result: bool = True
    ) -> Bundle | None:
        logger.debug(f"Dereferencing {rid!r}")
        
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
            self.processor.handle(
                bundle=bundle, 
                source=source if type(source) is KoiNetNode else None
            )

            # TODO: refactor for general solution, param to write through to cache before continuing
            # like `self.processor.kobj_queue.join()``

        return bundle