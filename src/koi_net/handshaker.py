import structlog
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode
from koi_net.identity import NodeIdentity
from koi_net.network.event_queue import EventQueue
from .protocol.event import Event, EventType

log = structlog.stdlib.get_logger()


class Handshaker:
    def __init__(
        self, 
        cache: Cache, 
        identity: NodeIdentity, 
        event_queue: EventQueue
    ):
        self.cache = cache
        self.identity = identity
        self.event_queue = event_queue
        
    def handshake_with(self, target: KoiNetNode):
        """Initiates a handshake with target node.
        Pushes successive `FORGET` and `NEW` events to target node to
        reset the target's cache in case it already knew this node. 
        """
        log.debug(f"Initiating handshake with {target}")
        self.event_queue.push_event_to(
            Event.from_rid(
                event_type=EventType.FORGET, 
                rid=self.identity.rid),
            target=target
        )
        self.event_queue.push_event_to(
            event=Event.from_bundle(
                event_type=EventType.NEW, 
                bundle=self.cache.read(self.identity.rid)),
            target=target
        )