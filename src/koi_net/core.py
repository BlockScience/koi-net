from rid_lib.ext import Cache
from .network import NetworkInterface
from .processor import ProcessorInterface

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
        self.processor = ProcessorInterface(self.cache, self.network)