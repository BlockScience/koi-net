import structlog
from queue import Queue

from rid_lib.types import KoiNetNode

from ..models import QueuedEvent
from ..protocol.event import Event

log = structlog.stdlib.get_logger()


class EventQueue:
    """Handles out going network event queues."""
    q: Queue[QueuedEvent]
    
    def __init__(self):
        self.q = Queue()
    
    def push_event_to(self, event: Event, target: KoiNetNode):
        """Pushes event to queue of specified node.
        
        Event will be sent to webhook or poll queue depending on the 
        node type and edge type of the specified node. If `flush` is set 
        to `True`, the webhook queued will be flushed after pushing the 
        event.
        """
        
        self.q.put(QueuedEvent(target=target, event=event))
    