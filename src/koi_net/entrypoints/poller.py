
import threading
import time
from logging import Logger

from ..logging_context import LoggingContext
from ..build.component import depends_on
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
        log: Logger,
        logging_context: LoggingContext,
        config: PartialNodeConfig,
        kobj_queue: KobjQueue,
        resolver: NetworkResolver
    ):
        super().__init__(log=log, logging_context=logging_context, name="poller")
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
    
    @depends_on("graph")
    def start(self):
        self.exit_event.clear()
        super().start()
    
    def stop(self):
        self.exit_event.set()
        super().stop()