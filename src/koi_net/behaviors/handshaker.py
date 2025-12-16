import structlog
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode

from ..network.graph import NetworkGraph
from ..config.base import BaseNodeConfig
from ..identity import NodeIdentity
from ..network.event_queue import EventQueue
from ..protocol.event import Event, EventType

log = structlog.stdlib.get_logger()


class Handshaker:
    """Handles handshaking with other nodes."""
    def __init__(
        self, 
        cache: Cache, 
        identity: NodeIdentity, 
        event_queue: EventQueue,
        config: BaseNodeConfig,
        graph: NetworkGraph
    ):
        self.config = config
        self.cache = cache
        self.identity = identity
        self.event_queue = event_queue
        self.graph = graph
        
    def start(self):
        """Attempts handshake with first contact on startup.
        
        Handshake occurs if first contact is set in the config, the first
        contact is not already known to this node, and this node does not
        already have incoming edges with node providers.
        """
        if not self.config.koi_net.first_contact.rid:
            return
        
        if self.cache.read(self.config.koi_net.first_contact.rid):
            return
        
        if self.graph.get_neighbors(
            direction="in", allowed_type=KoiNetNode):
            return
        
        self.handshake_with(self.config.koi_net.first_contact.rid)
        
    def handshake_with(self, target: KoiNetNode):
        """Initiates a handshake with target node.
        
        Pushes successive `FORGET` and `NEW` events to target node to
        reset the target's cache in case it already knew this node. 
        """
        
        log.debug(f"Initiating handshake with {target}")
        self.event_queue.push(
            Event.from_rid(
                event_type=EventType.FORGET, 
                rid=self.identity.rid),
            target=target
        )
        self.event_queue.push(
            event=Event.from_bundle(
                event_type=EventType.NEW, 
                bundle=self.cache.read(self.identity.rid)),
            target=target
        )