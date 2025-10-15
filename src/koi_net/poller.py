
import time
import structlog

from koi_net.interfaces.entrypoint import EntryPoint
from .processor.kobj_queue import KobjQueue
from .lifecycle import NodeLifecycle
from .network.resolver import NetworkResolver
from .config import NodeConfig

log = structlog.stdlib.get_logger()


class NodePoller(EntryPoint):
    """Manages polling based event loop for partial nodes."""
    kobj_queue: KobjQueue
    lifecycle: NodeLifecycle
    resolver: NetworkResolver
    config: NodeConfig
    
    def __init__(
        self,
        config: NodeConfig,
        lifecycle: NodeLifecycle,
        kobj_queue: KobjQueue,
        resolver: NetworkResolver,
    ):
        self.kobj_queue = kobj_queue
        self.lifecycle = lifecycle
        self.resolver = resolver
        self.config = config

    def poll(self):
        """Polls neighbors and processes returned events."""
        neighbors = self.resolver.poll_neighbors()
        for node_rid in neighbors:
            for event in neighbors[node_rid]:
                self.kobj_queue.put_kobj(event=event, source=node_rid)

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