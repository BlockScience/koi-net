import structlog
from contextlib import contextmanager, asynccontextmanager

from rid_lib.ext import Bundle
from rid_lib.types import KoiNetNode

from .sync_manager import SyncManager
from .handshaker import Handshaker
from .workers.kobj_worker import KnowledgeProcessingWorker
from .network.event_queue import EventQueue
from .workers import EventProcessingWorker
from .workers.base import STOP_WORKER
from .config.core import NodeConfig
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
    handshaker: Handshaker
    sync_manager: SyncManager
    
    def __init__(
        self,
        config: NodeConfig,
        identity: NodeIdentity,
        graph: NetworkGraph,
        kobj_queue: KobjQueue,
        kobj_worker: KnowledgeProcessingWorker,
        event_queue: EventQueue,
        event_worker: EventProcessingWorker,
        handshaker: Handshaker,
        sync_manager: SyncManager
    ):
        self.config = config
        self.identity = identity
        self.graph = graph
        self.kobj_queue = kobj_queue
        self.kobj_worker = kobj_worker
        self.event_queue = event_queue
        self.event_worker = event_worker
        self.handshaker = handshaker
        self.sync_manager = sync_manager
        
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
        self.kobj_worker.thread.start()
        self.event_worker.thread.start()
        self.graph.generate()
        
        # refresh to reflect changes (if any) in config.yaml node profile
        self.kobj_queue.push(bundle=Bundle.generate(
            rid=self.identity.rid,
            contents=self.identity.profile.model_dump()
        ))
        
        self.kobj_queue.q.join()
        
        node_providers = self.graph.get_neighbors(
            direction="in",
            allowed_type=[KoiNetNode]
        )
        
        if node_providers:
            log.debug(f"Catching up with `orn:koi-net.node` providers: {node_providers}")
            self.sync_manager.catch_up_with(node_providers, [KoiNetNode])
        
        elif self.config.koi_net.first_contact.rid:
            log.debug(f"No edges with `orn:koi-net.node` providers, reaching out to first contact {self.config.koi_net.first_contact.rid!r}")
            self.handshaker.handshake_with(self.config.koi_net.first_contact.rid)
            
    def stop(self):
        """Stops a node, send stop signals to workers."""
        
        self.kobj_queue.q.put(STOP_WORKER)
        self.event_queue.q.put(STOP_WORKER)