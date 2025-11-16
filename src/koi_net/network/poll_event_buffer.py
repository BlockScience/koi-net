from rid_lib.types import KoiNetNode

from ..protocol.event import Event


class PollEventBuffer:
    """Stores outgoing events intended for polling nodes."""
    buffers: dict[KoiNetNode, list[Event]]
    
    def __init__(self):
        self.buffers = dict()
        
    def push(self, node: KoiNetNode, event: Event):
        """Pushes event to specified node."""
        event_buf = self.buffers.setdefault(node, [])
        event_buf.append(event)
        
    def flush(self, node: KoiNetNode, limit: int = 0) -> list[Event]:
        """Flushes all events for a given node, with an optional limit."""
        event_buf = self.buffers.get(node, [])
        
        if limit and len(event_buf) > limit:
            flushed_events = event_buf[:limit]
            self.buffers[node] = event_buf[limit:]
        else:
            flushed_events = event_buf.copy()
            self.buffers[node] = []
        
        return flushed_events