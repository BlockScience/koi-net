import logging
from contextlib import contextmanager, asynccontextmanager

from koi_net.context import HandlerContext

from .network.behavior import Actor
from .effector import Effector
from .config import NodeConfig
from .processor.interface import ProcessorInterface
from .network.graph import NetworkGraph
from .identity import NodeIdentity

logger = logging.getLogger(__name__)


class NodeLifecycle:
    config: NodeConfig
    graph: NetworkGraph
    processor: ProcessorInterface
    effector: Effector
    actor: Actor
    
    def __init__(
        self,
        config: NodeConfig,
        identity: NodeIdentity,
        graph: NetworkGraph,
        processor: ProcessorInterface,
        effector: Effector,
        actor: Actor,
        handler_context: HandlerContext,
        use_kobj_processor_thread: bool
    ):
        self.config = config
        self.identity = identity
        self.graph = graph
        self.processor = processor
        self.effector = effector
        self.actor = actor
        self.handler_context = handler_context
        self.use_kobj_processor_thread = use_kobj_processor_thread
        
    @contextmanager
    def run(self):
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
        """Starts a node, call this method first.
        
        Starts the processor thread (if enabled). Loads event queues into memory. Generates network graph from nodes and edges in cache. Processes any state changes of node bundle. Initiates handshake with first contact (if provided) if node doesn't have any neighbors.
        """
        if self.use_kobj_processor_thread:
            logger.info("Starting processor worker thread")
            self.processor.worker_thread.start()
        
        self.graph.generate()
        
        # refresh to reflect changes (if any) in config.yaml
        self.effector.deref(self.identity.rid, refresh_cache=True)
        
        logger.debug("Waiting for kobj queue to empty")
        if self.use_kobj_processor_thread:
            self.processor.kobj_queue.join()
        else:
            self.processor.flush_kobj_queue()
        logger.debug("Done")
    
        if not self.graph.get_neighbors() and self.config.koi_net.first_contact.rid:
            logger.debug(f"I don't have any neighbors, reaching out to first contact {self.config.koi_net.first_contact.rid!r}")
            
            self.actor.handshake_with(self.config.koi_net.first_contact.rid)
            
                        
    def stop(self):
        """Stops a node, call this method last.
        
        Finishes processing knowledge object queue. Saves event queues to storage.
        """        
        if self.use_kobj_processor_thread:
            logger.info(f"Waiting for kobj queue to empty ({self.processor.kobj_queue.unfinished_tasks} tasks remaining)")
            self.processor.kobj_queue.join()
        else:
            self.processor.flush_kobj_queue()