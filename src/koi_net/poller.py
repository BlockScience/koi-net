
import time
import logging
from .processor.interface import ProcessorInterface
from .lifecycle import NodeLifecycle
from .network.resolver import NetworkResolver
from .config import NodeConfig

logger = logging.getLogger(__name__)


class NodePoller:
    """Manages polling based event loop for partial nodes."""
    processor: ProcessorInterface
    lifecycle: NodeLifecycle
    resolver: NetworkResolver
    config: NodeConfig
    
    def __init__(
        self,
        processor: ProcessorInterface,
        lifecycle: NodeLifecycle,
        resolver: NetworkResolver,
        config: NodeConfig
    ):
        self.processor = processor
        self.lifecycle = lifecycle
        self.resolver = resolver
        self.config = config

    def poll(self):
        """Polls neighbors and processes returned events."""
        neighbors = self.resolver.poll_neighbors()
        for node_rid in neighbors:
            for event in neighbors[node_rid]:
                self.processor.handle(event=event, source=node_rid)
        self.processor.flush_kobj_queue()

    def run(self):
        """Runs polling event loop."""
        with self.lifecycle.run():
            while True:
                start_time = time.time()
                self.poll()
                elapsed = time.time() - start_time
                sleep_time = self.config.koi_net.polling_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)