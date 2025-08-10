from logging import getLogger
from rid_lib.types import KoiNetNode
from ..protocol.event import Event, EventType
from ..identity import NodeIdentity
from ..effector import Effector
from ..network.event_queue import NetworkEventQueue

logger = getLogger(__name__)


class Actor:
    identity: NodeIdentity
    effector: Effector
    event_queue: NetworkEventQueue
    
    def __init__(
        self, 
        identity: NodeIdentity, 
        effector: Effector,
        event_queue: NetworkEventQueue
    ):
        self.identity = identity
        self.effector = effector
        self.event_queue = event_queue
    
    def handshake_with(self, target: KoiNetNode):
        logger.debug(f"Initiating handshake with {target}")
        self.event_queue.push_event_to(
            Event.from_rid(
                event_type=EventType.FORGET, 
                rid=self.identity.rid),
            node=target
        )
            
        self.event_queue.push_event_to(
            event=Event.from_bundle(
                event_type=EventType.NEW, 
                bundle=self.effector.deref(self.identity.rid)),
            node=target
        )
        
        self.event_queue.flush_webhook_queue(target)