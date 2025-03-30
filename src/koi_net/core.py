import logging
import httpx
from rid_lib.ext import Cache, Bundle
from rid_lib.types.koi_net_node import KoiNetNode

from .network import NetworkInterface
from .processor import ProcessorInterface, default_handlers
from .processor.handler import Handler
from .identity import NodeIdentity
from .protocol.event import Event, EventType
from .protocol.node import NodeProfile

logger = logging.getLogger(__name__)


class NodeInterface:
    def __init__(
        self, 
        rid: KoiNetNode,
        profile: NodeProfile,
        first_contact: str | None = None,
        cache: Cache | None = None,
        network: NetworkInterface | None = None,
        processor: ProcessorInterface | None = None
    ):
        self.cache = cache or Cache(directory_path="cache")
        self.identity = NodeIdentity(
            rid=rid, 
            profile=profile, 
            cache=cache
        )
        self.first_contact = first_contact
        self.network = network or NetworkInterface(
            file_path="event_queues.json", 
            first_contact=self.first_contact,
            cache=self.cache, 
            identity=self.identity
        )
        
        # pull all handlers defined in default_handlers module
        handlers = [
            obj for obj in vars(default_handlers).values() 
            if isinstance(obj, Handler)
        ]
        
        self.processor = processor or ProcessorInterface(self.cache, self.network, self.identity, handlers)
        
        
    def initialize(self):
        self.network.graph.generate()
        
        self.processor.handle(
            bundle=Bundle.generate(
                rid=self.identity.rid, 
                contents=self.identity.profile.model_dump()
            ),
            flush=True
        )
    
        if not self.network.graph.get_neighbors() and self.first_contact:
            logger.info(f"I don't have any neighbors, reaching out to first contact {self.first_contact}")
            
            events = [
                Event.from_rid(EventType.FORGET, self.identity.rid),
                Event.from_bundle(EventType.NEW, self.identity.bundle)
            ]
            
            try:
                self.network.adapter.broadcast_events(
                    url=self.first_contact,
                    events=events
                )
                
            except httpx.ConnectError:
                logger.info("Failed to reach first contact")
                return
            
            
                        
    def finalize(self):
        self.network.save_event_queues()