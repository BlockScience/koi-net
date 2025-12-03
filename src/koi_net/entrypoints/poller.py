
import time
import structlog

from .base import EntryPoint
from ..processor.kobj_queue import KobjQueue
from ..network.resolver import NetworkResolver
from ..config.partial_node import PartialNodeConfig

log = structlog.stdlib.get_logger()


class NodePoller(EntryPoint):
    """Entry point for partial nodes, manages polling event loop."""
    kobj_queue: KobjQueue
    resolver: NetworkResolver
    config: PartialNodeConfig
    
    def __init__(
        self,
        config: PartialNodeConfig,
        kobj_queue: KobjQueue,
        resolver: NetworkResolver
    ):
        self.kobj_queue = kobj_queue
        self.resolver = resolver
        self.config = config

    def poll(self):
        """Polls neighbor nodes and processes returned events."""
        for node_rid, events in self.resolver.poll_neighbors().items():
            for event in events:
                self.kobj_queue.push(event=event, source=node_rid)

    def run(self):
        """Runs polling event loop."""
        while True:
            start_time = time.time()
            self.poll()
            elapsed = time.time() - start_time
            sleep_time = self.config.poller.polling_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)