import time
from rid_lib.types import KoiNetNode

from ..protocol.event import Event


class EventBuffer:
    """Stores outgoing events intended for polling nodes."""
    buffers: dict[KoiNetNode, list[Event]]
    start_time: dict[KoiNetNode, float]
    
    def __init__(self):
        self.buffers = {}
        self.start_time = {}
        
    def push(self, node: KoiNetNode, event: Event):
        """Pushes event to specified node.
        
        Sets start time to now if unset.
        """
        
        if node not in self.buffers:
            self.start_time[node] = time.time()
        
        event_buf = self.buffers.setdefault(node, [])
        event_buf.append(event)
        
    def buf_len(self, node: KoiNetNode):
        """Returns the length of a node's event buffer."""
        return len(self.buffers.get(node, []))
        
    def flush(self, node: KoiNetNode, limit: int = 0) -> list[Event]:
        """Flushes all (or limit) events for a node.
        
        Resets start time.
        """
        
        if node in self.start_time:
            del self.start_time[node]
        
        if node not in self.buffers:
            return []
        
        event_buf = self.buffers[node]
        
        if limit and len(event_buf) > limit:
            flushed_events = event_buf[:limit]
            self.buffers[node] = event_buf[limit:]
        else:
            flushed_events = event_buf.copy()
            del self.buffers[node]
        
        return flushed_events