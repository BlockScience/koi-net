import structlog
from queue import Queue
from rid_lib.core import RID
from rid_lib.ext import Bundle, Manifest
from rid_lib.types import KoiNetNode
from ..protocol.event import Event, EventType
from .knowledge_object import KnowledgeObject

log = structlog.stdlib.get_logger()


class KobjQueue:
    """Provides access to this node's knowledge processing pipeline."""
    q: Queue[KnowledgeObject]
    
    def __init__(self):
        self.q = Queue()
                
    def put_kobj(
        self,
        rid: RID | None = None,
        manifest: Manifest | None = None,
        bundle: Bundle | None = None,
        event: Event | None = None,
        kobj: KnowledgeObject | None = None,
        event_type: EventType | None = None,
        source: KoiNetNode | None = None
    ):
        """Queues knowledge object to be handled by processing pipeline.
        
        Knowledge may take the form of an RID, manifest, bundle, event, 
        or knowledge object (with an optional event type for RID, 
        manifest, or bundle objects). All objects will be normalized 
        to knowledge objects and queued. If `flush` is `True`, the queue 
        will be flushed immediately after adding the new knowledge.
        """
        if rid:
            _kobj = KnowledgeObject.from_rid(rid, event_type, source)
        elif manifest:
            _kobj = KnowledgeObject.from_manifest(manifest, event_type, source)
        elif bundle:
            _kobj = KnowledgeObject.from_bundle(bundle, event_type, source)
        elif event:
            _kobj = KnowledgeObject.from_event(event, source)
        elif kobj:
            _kobj = kobj
        else:
            raise ValueError("One of 'rid', 'manifest', 'bundle', 'event', or 'kobj' must be provided")
        
        self.q.put(_kobj)
        log.debug(f"Queued {_kobj!r}")
