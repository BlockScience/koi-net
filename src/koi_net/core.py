import logging
import httpx
from rid_lib.ext import Cache, Bundle
from .network import NetworkInterface
from .processor import ProcessorInterface
from .processor import default_handlers
from .processor.handler import KnowledgeHandler
from .identity import NodeIdentity
from .protocol.node import NodeProfile
from .protocol.event import Event, EventType

logger = logging.getLogger(__name__)


class NodeInterface:
    cache: Cache
    identity: NodeIdentity
    network: NetworkInterface
    processor: ProcessorInterface
    first_contact: str
    use_kobj_processor_thread: bool
    
    def __init__(
        self, 
        name: str,
        profile: NodeProfile,
        identity_file_path: str = "identity.json",
        event_queues_file_path: str = "event_queues.json",
        cache_directory_path: str = "rid_cache",
        use_kobj_processor_thread: bool = False,
        first_contact: str | None = None,
        handlers: list[KnowledgeHandler] | None = None,
        cache: Cache | None = None,
        network: NetworkInterface | None = None,
        processor: ProcessorInterface | None = None
    ):
        self.cache = cache or Cache(cache_directory_path)
        self.identity = NodeIdentity(
            name=name,
            profile=profile,
            cache=self.cache,
            file_path=identity_file_path
        )
        self.first_contact = first_contact
        self.network = network or NetworkInterface(
            file_path=event_queues_file_path, 
            first_contact=self.first_contact,
            cache=self.cache, 
            identity=self.identity
        )
        
        # pull all handlers defined in default_handlers module
        if not handlers:
            handlers = [
                obj for obj in vars(default_handlers).values() 
                if isinstance(obj, KnowledgeHandler)
            ]

        self.use_kobj_processor_thread = use_kobj_processor_thread
        self.processor = processor or ProcessorInterface(
            cache=self.cache, 
            network=self.network, 
            identity=self.identity, 
            use_kobj_processor_thread=self.use_kobj_processor_thread,
            default_handlers=handlers
        )
    
    def start(self) -> None:
        """Starts a node, call this method first.
        
        Starts the processor thread (if enabled). Loads event queues into memory. Generates network graph from nodes and edges in cache. Processes any state changes of node bundle. Initiates handshake with first contact (if provided) if node doesn't have any neighbors.
        """
        if self.use_kobj_processor_thread:
            logger.info("Starting processor worker thread")
            self.processor.worker_thread.start()
        
        self.network._load_event_queues()
        self.network.graph.generate()
        
        self.processor.handle(
            bundle=Bundle.generate(
                rid=self.identity.rid, 
                contents=self.identity.profile.model_dump()
            )
        )
        
        logger.info("Waiting for kobj queue to empty")
        if self.use_kobj_processor_thread:
            self.processor.kobj_queue.join()
        else:
            self.processor.flush_kobj_queue()
        logger.info("Done")
    
        if not self.network.graph.get_neighbors() and self.first_contact:
            logger.info(f"I don't have any neighbors, reaching out to first contact {self.first_contact}")
            
            events = [
                Event.from_rid(EventType.FORGET, self.identity.rid),
                Event.from_bundle(EventType.NEW, self.identity.bundle)
            ]
            
            try:
                self.network.request_handler.broadcast_events(
                    url=self.first_contact,
                    events=events
                )
                
            except httpx.ConnectError:
                logger.info("Failed to reach first contact")
                return
            
                        
    def stop(self):
        """Stops a node, call this method last.
        
        Finishes processing knowledge object queue. Saves event queues to storage.
        """
        logger.info("Stopping node...")
        
        if self.use_kobj_processor_thread:
            logger.info("Waiting for kobj queue to empty")
            self.processor.kobj_queue.join()
        else:
            self.processor.flush_kobj_queue()
        
        self.network._save_event_queues()