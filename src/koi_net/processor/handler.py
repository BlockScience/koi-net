from dataclasses import dataclass
from enum import StrEnum
from typing import Callable
from rid_lib.core import RIDType

from ..protocol.event import EventType
from .knowledge_object import KnowledgeObject
from .context import HandlerContext


class StopChain:
    """Class for STOP_CHAIN sentinel returned by knowledge handlers."""
    pass

STOP_CHAIN = StopChain()


class HandlerType(StrEnum):
    """Types of handlers used in knowledge processing pipeline.
    
    - RID - provided RID; if event type is `FORGET`, this handler decides whether to delete the knowledge from the cache by setting the normalized event type to `FORGET`, otherwise this handler decides whether to validate the manifest (and fetch it if not provided).
    - Manifest - provided RID, manifest; decides whether to validate the bundle (and fetch it if not provided).
    - Bundle - provided RID, manifest, contents (bundle); decides whether to write knowledge to the cache by setting the normalized event type to `NEW` or `UPDATE`.
    - Network - provided RID, manifest, contents (bundle); decides which nodes (if any) to broadcast an event about this knowledge to. (Note, if event type is `FORGET`, the manifest and contents will be retrieved from the local cache, and indicate the last state of the knowledge before it was deleted.)
    - Final - provided RID, manifests, contents (bundle); final action taken after network broadcast.
    """
    
    RID = "rid", 
    Manifest = "manifest", 
    Bundle = "bundle", 
    Network = "network", 
    Final = "final"

@dataclass
class KnowledgeHandler:
    """Handles knowledge processing events of the provided types."""
    
    func: Callable[[HandlerContext, KnowledgeObject], None | KnowledgeObject | StopChain]
    handler_type: HandlerType
    rid_types: tuple[RIDType] = ()
    event_types: tuple[EventType | None] = ()
    
    def __call__(
        self, 
        ctx: HandlerContext, 
        kobj: KnowledgeObject
    ) -> None | KnowledgeObject | StopChain:
        return self.func(ctx, kobj)
    
    @classmethod
    def create(
        cls,
        handler_type: HandlerType,
        rid_types: tuple[RIDType] = (),
        event_types: tuple[EventType | None] = ()
    ):
        """Decorator wraps a function, returns a KnowledgeHandler."""
        def decorator(func: Callable) -> KnowledgeHandler:
            handler = cls(func, handler_type, rid_types, event_types)
            return handler
        return decorator
