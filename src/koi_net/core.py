from rid_lib.ext import Cache
from .network import NetworkInterface
from .processor import ProcessorInterface, default_handlers

class NodeInterface:
    def __init__(
        self, 
        rid,
        cache: Cache | None = None,
        network: NetworkInterface | None = None,
        processor: ProcessorInterface | None = None,
    ):
        self.rid = rid
        self.cache = cache or Cache("cache")
        self.network = network or NetworkInterface("event_queues.json", self.cache, self.rid)
        self.processor = processor or ProcessorInterface(self.cache, self.network,
            default_handlers=[
                default_handlers.koi_net_graph_handler,
                default_handlers.basic_state_handler
            ]
        )