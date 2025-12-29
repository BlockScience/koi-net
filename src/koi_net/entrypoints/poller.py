
import threading
import time
import structlog

from ..processor.kobj_queue import KobjQueue
from ..network.resolver import NetworkResolver
from ..config.partial_node import PartialNodeConfig

log = structlog.stdlib.get_logger()


class NodePoller:
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
        self.should_exit = False
        
        self.thread = threading.Thread(target=self.run)

    def poll(self):
        """Polls neighbor nodes and processes returned events."""
        for node_rid, events in self.resolver.poll_neighbors().items():
            for event in events:
                self.kobj_queue.push(event=event, source=node_rid)

    def run(self):
        """Runs polling event loop."""
        while not self.should_exit:
            start_time = time.time()
            self.poll()
            elapsed = time.time() - start_time
            sleep_time = self.config.poller.polling_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
                
    def start(self):
        self.thread.start()
        
    def stop(self):
        self.should_exit = True
        if self.thread.is_alive():
            self.thread.join()