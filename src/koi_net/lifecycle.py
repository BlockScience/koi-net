import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Callable

from rid_lib.ext import Bundle, Cache
from rid_lib.types import KoiNetNode

from koi_net.kobj_worker import KnowledgeProcessingWorker
from koi_net.models import END
from koi_net.network.event_queue import EventQueue
from koi_net.processor.event_worker import EventProcessingWorker

from .config import NodeConfig
from .processor.kobj_queue import KobjQueue
from .network.graph import NetworkGraph
from .identity import NodeIdentity

logger = logging.getLogger(__name__)


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
        handshake_with: Callable,
        catch_up_with: Callable,
        identify_coordinators: Callable
    ):
        self.config = config
        self.identity = identity
        self.graph = graph
        self.kobj_queue = kobj_queue
        self.kobj_worker = kobj_worker
        self.event_queue = event_queue
        self.event_worker = event_worker
        self.cache = cache
        
        self.handshake_with = handshake_with
        self.catch_up_with = catch_up_with
        self.identify_coordinators = identify_coordinators
        
    @contextmanager
    def run(self):
        """Synchronous context manager for node startup and shutdown."""
        try:
            logger.info("Starting node lifecycle...")
            self.start()
            yield
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt!")
        finally:
            logger.info("Stopping node lifecycle...")
            self.stop()

    @asynccontextmanager
    async def async_run(self):
        """Asynchronous context manager for node startup and shutdown."""
        try:
            logger.info("Starting async node lifecycle...")
            self.start()
            yield
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt!")
        finally:
            logger.info("Stopping async node lifecycle...")
            self.stop()
    
    def start(self):
        """Starts a node.
        
        Starts the processor thread (if enabled). Generates network 
        graph from nodes and edges in cache. Processes any state changes 
        of node bundle. Initiates handshake with first contact if node 
        doesn't have any neighbors. Catches up with coordinator state.
        """
        logger.info("Starting processor worker thread")
        
        self.kobj_worker.thread.start()
        self.event_worker.thread.start()
        self.graph.generate()
        
        # refresh to reflect changes (if any) in config.yaml                
        
        self.kobj_queue.put_kobj(bundle=Bundle.generate(
            rid=self.identity.rid,
            contents=self.identity.profile.model_dump()
        ))
        
        logger.debug("Waiting for kobj queue to empty")
        
        # TODO: REFACTOR
        self.kobj_queue.q.join()
        
        # TODO: FACTOR OUT BEHAVIOR
        if not self.graph.get_neighbors() and self.config.koi_net.first_contact.rid:
            logger.debug(f"I don't have any neighbors, reaching out to first contact {self.config.koi_net.first_contact.rid!r}")
            
            self.handshake_with(self.config.koi_net.first_contact.rid)
        
        for coordinator in self.identify_coordinators():
            self.catch_up_with(coordinator, rid_types=[KoiNetNode])
        

    def stop(self):
        """Stops a node.
        
        Finishes processing knowledge object queue.
        """        
        logger.info(f"Waiting for kobj queue to empty ({self.kobj_queue.q.unfinished_tasks} tasks remaining)")
        
        self.kobj_queue.q.put(END)
        self.event_queue.q.put(END)