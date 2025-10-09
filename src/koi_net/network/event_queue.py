import structlog
from queue import Queue

from rid_lib.types import KoiNetNode
from pydantic import BaseModel

from ..protocol.event import Event

log = structlog.stdlib.get_logger()


class QueuedEvent(BaseModel):
    event: Event
    target: KoiNetNode

class EventQueue:
    """Handles out going network event queues."""
    q: Queue[QueuedEvent]
    
    def __init__(self):
        self.q = Queue()
    
    def push_event_to(self, event: Event, target: KoiNetNode):
        """Pushes event to queue of specified node.
        
        Event will be sent to webhook or poll queue depending on the 
        node type and edge type of the specified node.
        """
        
        self.q.put(QueuedEvent(target=target, event=event))
    