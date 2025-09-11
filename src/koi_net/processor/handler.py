from dataclasses import dataclass
from enum import StrEnum
from typing import Callable
from rid_lib import RIDType
from ..protocol.event import EventType


class StopChain:
    """Class for a sentinel value by knowledge handlers."""
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
    
    func: Callable
    handler_type: HandlerType
    rid_types: list[RIDType] | None
    event_types: list[EventType | None] | None = None
    
    @classmethod
    def create(
        cls,
        handler_type: HandlerType,
        rid_types: list[RIDType] | None = None,
        event_types: list[EventType | None] | None = None
    ):
        """Decorator wraps a function, returns a KnowledgeHandler.
        
        The function symbol will redefined as a `KnowledgeHandler`, 
        which can be passed into the `ProcessorInterface` constructor. 
        This is used to register default handlers.
        """
        def decorator(func: Callable) -> KnowledgeHandler:
            handler = cls(func, handler_type, rid_types, event_types)
            return handler
        return decorator

