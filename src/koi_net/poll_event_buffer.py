from rid_lib.types import KoiNetNode

from koi_net.protocol.event import Event


class PollEventBuffer:
    buffers: dict[KoiNetNode, list[Event]]
    
    def __init__(self):
        self.buffers = dict()
        
    def put(self, node: KoiNetNode, event: Event):
        event_buf = self.buffers.setdefault(node, [])
        event_buf.append(event)
        
    def flush(self, node: KoiNetNode):
        return self.buffers.pop(node, [])