import structlog
from koi_net.handshaker import Handshaker
from koi_net.protocol.errors import ErrorType
from koi_net.protocol.event import EventType
from rid_lib.types import KoiNetNode
from ..processor.kobj_queue import KobjQueue

log = structlog.stdlib.get_logger()


class ErrorHandler:
    """Handles network errors that may occur during requests."""
    timeout_counter: dict[KoiNetNode, int]
    kobj_queue: KobjQueue
    
    def __init__(
        self, 
        kobj_queue: KobjQueue,
        handshaker: Handshaker
    ):
        self.kobj_queue = kobj_queue
        self.handshaker = handshaker
        self.timeout_counter = {}
        
    def handle_connection_error(self, node: KoiNetNode):
        """Drops nodes after timing out three times."""
        self.timeout_counter.setdefault(node, 0)
        self.timeout_counter[node] += 1
        
        log.debug(f"{node} has timed out {self.timeout_counter[node]} time(s)")
        
        if self.timeout_counter[node] > 3:
            log.debug(f"Exceeded time out limit, forgetting node")
            self.kobj_queue.put_kobj(rid=node, event_type=EventType.FORGET)
            # do something
        
        
    def handle_protocol_error(
        self, 
        error_type: ErrorType, 
        node: KoiNetNode
    ):
        """Attempts handshake when this node is unknown to target."""
        log.info(f"Handling protocol error {error_type} for node {node!r}")
        match error_type:
            case ErrorType.UnknownNode:
                log.info("Peer doesn't know me, attempting handshake...")
                self.handshaker.handshake_with(node)
                
            case ErrorType.InvalidKey: ...
            case ErrorType.InvalidSignature: ...
            case ErrorType.InvalidTarget: ...
