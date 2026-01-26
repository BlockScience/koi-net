
import threading
import time
from logging import Logger

from ..build import comp_order
from ..build.threaded_component import ThreadedComponent
from ..processor.kobj_queue import KobjQueue
from ..network.resolver import NetworkResolver
from ..config.partial_node import PartialNodeConfig


class NodePoller(ThreadedComponent):
    """Entry point for partial nodes, manages polling event loop."""
    kobj_queue: KobjQueue
    resolver: NetworkResolver
    config: PartialNodeConfig
    
    def __init__(
        self,
        config: PartialNodeConfig,
        root_dir,
        kobj_queue: KobjQueue,
        resolver: NetworkResolver,
        log: Logger
    ):
        self.log = log
        self.root_dir = root_dir
        self.kobj_queue = kobj_queue
        self.resolver = resolver
        self.config = config
        self.exit_event = threading.Event()
        
    def poll(self):
        """Polls neighbor nodes and processes returned events."""
        for node_rid, events in self.resolver.poll_neighbors().items():
            for event in events:
                self.kobj_queue.push(event=event, source=node_rid)

    def run(self):
        """Runs polling event loop."""
        while not self.exit_event.is_set():
            start_time = time.monotonic()
            self.poll()
            elapsed = time.monotonic() - start_time
            wait_time = max(0, self.config.poller.polling_interval - elapsed)
            self.exit_event.wait(wait_time)
    
    @comp_order.start_after("graph")
    def start(self):
        self.exit_event.clear()
        super().start()
    
    def stop(self):
        self.exit_event.set()
        super().stop()