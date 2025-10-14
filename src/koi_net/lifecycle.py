import structlog
from contextlib import contextmanager, asynccontextmanager

from rid_lib.ext import Bundle, Cache
from rid_lib.types import KoiNetNode

from .handshaker import Handshaker
from .network.request_handler import RequestHandler
from .processor.kobj_worker import KnowledgeProcessingWorker
from .network.event_queue import EventQueue
from .processor.event_worker import EventProcessingWorker
from .protocol.api_models import ErrorResponse
from .interfaces.worker import STOP_WORKER
from .config import NodeConfig
from .processor.kobj_queue import KobjQueue
from .network.graph import NetworkGraph
from .identity import NodeIdentity

log = structlog.stdlib.get_logger()


class NodeLifecycle:
    """Manages node startup and shutdown processes."""
    
    config: NodeConfig
    identity: NodeIdentity
    graph: NetworkGraph
    kobj_queue: KobjQueue
    kobj_worker: KnowledgeProcessingWorker
    event_queue: EventQueue
    event_worker: EventProcessingWorker
    cache: Cache
    handshaker: Handshaker
    request_handler: RequestHandler
    
    def __init__(
        self,
        config: NodeConfig,
        identity: NodeIdentity,
        graph: NetworkGraph,
        kobj_queue: KobjQueue,
        kobj_worker: KnowledgeProcessingWorker,
        event_queue: EventQueue,
        event_worker: EventProcessingWorker,
        cache: Cache,
        handshaker: Handshaker,
        request_handler: RequestHandler
    ):
        self.config = config
        self.identity = identity
        self.graph = graph
        self.kobj_queue = kobj_queue
        self.kobj_worker = kobj_worker
        self.event_queue = event_queue
        self.event_worker = event_worker
        self.cache = cache
        self.handshaker = handshaker
        self.request_handler = request_handler
        
    @contextmanager
    def run(self):
        """Synchronous context manager for node startup and shutdown."""
        try:
            log.info("Starting node lifecycle...")
            self.start()
            yield
        except KeyboardInterrupt:
            log.info("Keyboard interrupt!")
        finally:
            log.info("Stopping node lifecycle...")
            self.stop()

    @asynccontextmanager
    async def async_run(self):
        """Asynchronous context manager for node startup and shutdown."""
        try:
            log.info("Starting async node lifecycle...")
            self.start()
            yield
        except KeyboardInterrupt:
            log.info("Keyboard interrupt!")
        finally:
            log.info("Stopping async node lifecycle...")
            self.stop()
    
    def start(self):
        """Starts a node.
        
        Starts the processor thread (if enabled). Generates network 
        graph from nodes and edges in cache. Processes any state changes 
        of node bundle. Initiates handshake with first contact if node 
        doesn't have any neighbors. Catches up with coordinator state.
        """
        log.info("Starting processor worker thread")
        
        self.kobj_worker.thread.start()
        self.event_worker.thread.start()
        self.graph.generate()
        
        # refresh to reflect changes (if any) in config.yaml
        
        self.kobj_queue.put_kobj(bundle=Bundle.generate(
            rid=self.identity.rid,
            contents=self.identity.profile.model_dump()
        ))
        
        log.debug("Waiting for kobj queue to empty")
        self.kobj_queue.q.join()
        
        coordinators = self.graph.get_neighbors(direction="in", allowed_type=KoiNetNode)
        
        if len(coordinators) > 0:
            for coordinator in coordinators:
                payload = self.request_handler.fetch_manifests(
                    node=coordinator,
                    rid_types=[KoiNetNode]
                )
                if type(payload) is ErrorResponse:
                    continue
                
                for manifest in payload.manifests:
                    self.kobj_queue.put_kobj(
                        manifest=manifest,
                        source=coordinator
                    )
                    
        elif self.config.koi_net.first_contact.rid:
            log.debug(f"I don't have any edges with coordinators, reaching out to first contact {self.config.koi_net.first_contact.rid!r}")
            
            self.handshaker.handshake_with(self.config.koi_net.first_contact.rid)
        

    def stop(self):
        """Stops a node.
        
        Finishes processing knowledge object queue.
        """        
        log.info(f"Waiting for kobj queue to empty ({self.kobj_queue.q.unfinished_tasks} tasks remaining)")
        
        self.kobj_queue.q.put(STOP_WORKER)
        self.event_queue.q.put(STOP_WORKER)