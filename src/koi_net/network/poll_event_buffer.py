from rid_lib.types import KoiNetNode

from koi_net.protocol.event import Event


class PollEventBuffer:
    buffers: dict[KoiNetNode, list[Event]]
    
    def __init__(self):
        self.buffers = dict()
        
    def put(self, node: KoiNetNode, event: Event):
        event_buf = self.buffers.setdefault(node, [])
        event_buf.append(event)
        
    def flush(self, node: KoiNetNode, limit: int = 0):
        event_buf = self.buffers.get(node, [])
        
        if limit and len(event_buf) > limit:
            to_return = event_buf[:limit]
            self.buffers[node] = event_buf[limit:]
        else:
            to_return = event_buf.copy()
            self.buffers[node] = []
        
        return to_return