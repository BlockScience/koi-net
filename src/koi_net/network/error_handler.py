from logging import getLogger
from typing import Callable
from koi_net.behaviors import Behaviors
from koi_net.protocol.errors import ErrorType
from koi_net.protocol.event import EventType
from rid_lib.types import KoiNetNode
from ..processor.kobj_queue import KobjQueue

logger = getLogger(__name__)


class ErrorHandler:
    """Handles network errors that may occur during requests."""
    timeout_counter: dict[KoiNetNode, int]
    kobj_queue: KobjQueue
    
    def __init__(
        self, 
        kobj_queue: KobjQueue,
        behaviors: Behaviors
    ):
        self.kobj_queue = kobj_queue
        self.behaviors = behaviors
        self.timeout_counter = {}
        
    def handle_connection_error(self, node: KoiNetNode):
        """Drops nodes after timing out three times."""
        self.timeout_counter.setdefault(node, 0)
        self.timeout_counter[node] += 1
        
        logger.debug(f"{node} has timed out {self.timeout_counter[node]} time(s)")
        
        if self.timeout_counter[node] > 3:
            logger.debug(f"Exceeded time out limit, forgetting node")
            self.kobj_queue.put_kobj(rid=node, event_type=EventType.FORGET)
            # do something
        
        
    def handle_protocol_error(
        self, 
        error_type: ErrorType, 
        node: KoiNetNode
    ):
        """Attempts handshake when this node is unknown to target."""
        logger.info(f"Handling protocol error {error_type} for node {node!r}")
        match error_type:
            case ErrorType.UnknownNode:
                logger.info("Peer doesn't know me, attempting handshake...")
                self.behaviors.handshake_with(node)
                
            case ErrorType.InvalidKey: ...
            case ErrorType.InvalidSignature: ...
            case ErrorType.InvalidTarget: ...
