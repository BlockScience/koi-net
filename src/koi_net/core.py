import logging
import httpx
from rid_lib.ext import Cache, Bundle
from .network.interface import NetworkInterface
from .network.graph import NetworkGraph
from .network.request_handler import RequestHandler
from .network.response_handler import ResponseHandler
from .processor.interface import ProcessorInterface
from .processor import default_handlers
from .processor.handler import KnowledgeHandler
from .identity import NodeIdentity
from .secure import Secure
from .protocol.event import Event, EventType
from .config import NodeConfig
from .processor.handler_context import HandlerContext
from .effector import Effector
from . import default_actions

logger = logging.getLogger(__name__)



class NodeInterface:
    config: NodeConfig
    cache: Cache
    identity: NodeIdentity
    network: NetworkInterface
    graph: NetworkGraph
    processor: ProcessorInterface
    secure: Secure
    
    use_kobj_processor_thread: bool
    
    def __init__(
        self, 
        config: NodeConfig,
        use_kobj_processor_thread: bool = False,
        
        handlers: list[KnowledgeHandler] | None = None,
        
        cache: Cache | None = None,
        network: NetworkInterface | None = None,
        processor: ProcessorInterface | None = None
    ):
        self.config = config
        self.cache = cache or Cache(
            self.config.koi_net.cache_directory_path)
        
        self.identity = NodeIdentity(self.config)
        
        self.effector = Effector(self.cache)

        self.graph = NetworkGraph(self.cache, self.identity)
        
        self.secure = Secure(self.identity, self.effector)
        
        self.request_handler = RequestHandler(
            self.effector, 
            self.identity,
            self.secure
        )
        
        self.response_handler = ResponseHandler(self.cache, self.effector)
        
        self.network = network or NetworkInterface(
            config=self.config,
            cache=self.cache, 
            identity=self.identity,
            graph=self.graph,
            request_handler=self.request_handler,
            effector=self.effector
        )
        
        # pull all handlers defined in default_handlers module
        if handlers is None:
            handlers = [
                obj for obj in vars(default_handlers).values() 
                if isinstance(obj, KnowledgeHandler)
            ]

        self.use_kobj_processor_thread = use_kobj_processor_thread
        
        self.handler_context = HandlerContext(
            identity=self.identity,
            cache=self.cache,
            network=self.network,
            graph=self.graph,
            request_handler=self.request_handler
        )
        
        self.processor = processor or ProcessorInterface(
            handler_context=self.handler_context,
            cache=self.cache, 
            graph=self.graph,
            network=self.network, 
            use_kobj_processor_thread=self.use_kobj_processor_thread,
            default_handlers=handlers
        )
        
        self.handler_context.set_processor(self.processor)
        
        self.effector.set_processor(self.processor)
        self.effector.set_network(self.network)
        self.effector.set_handler_context(self.handler_context)
         
            
    def start(self) -> None:
        """Starts a node, call this method first.
        
        Starts the processor thread (if enabled). Loads event queues into memory. Generates network graph from nodes and edges in cache. Processes any state changes of node bundle. Initiates handshake with first contact (if provided) if node doesn't have any neighbors.
        """
        if self.use_kobj_processor_thread:
            logger.info("Starting processor worker thread")
            self.processor.worker_thread.start()
        
        # self.network._load_event_queues()
        self.graph.generate()
        
        self.effector.deref(self.identity.rid)
                
        logger.debug("Waiting for kobj queue to empty")
        if self.use_kobj_processor_thread:
            self.processor.kobj_queue.join()
        else:
            self.processor.flush_kobj_queue()
        logger.debug("Done")
    
        if not self.graph.get_neighbors() and self.config.koi_net.first_contact_rid:
            logger.debug(f"I don't have any neighbors, reaching out to first contact {self.config.koi_net.first_contact_rid}")
            
            events = [
                Event.from_rid(EventType.FORGET, self.identity.rid),
                Event.from_bundle(EventType.NEW, self.effector.deref(self.identity.rid))
            ]
            
            try:
                self.request_handler.broadcast_events(
                    node=self.config.koi_net.first_contact_rid,
                    events=events
                )
                
            except httpx.ConnectError:
                logger.warning("Failed to reach first contact")
                return
            
                        
    def stop(self):
        """Stops a node, call this method last.
        
        Finishes processing knowledge object queue. Saves event queues to storage.
        """
        logger.info("Stopping node...")
        
        if self.use_kobj_processor_thread:
            logger.info(f"Waiting for kobj queue to empty ({self.processor.kobj_queue.unfinished_tasks} tasks remaining)")
            self.processor.kobj_queue.join()
        else:
            self.processor.flush_kobj_queue()
        
        # self.network._save_event_queues()