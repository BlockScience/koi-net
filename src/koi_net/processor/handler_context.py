
from koi_net.network_graph import NetworkGraph
from koi_net.network_interface import NetworkInterface
from koi_net.request_handler import RequestHandler
from rid_lib.ext import Cache
from koi_net.identity import NodeIdentity

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from koi_net.processor.interface import ProcessorInterface


class HandlerContext:
    identity: NodeIdentity
    cache: Cache
    network: NetworkInterface
    graph: NetworkGraph
    request_handler: RequestHandler
    _processor: "ProcessorInterface | None"
    
    def __init__(
        self,
        identity: NodeIdentity,
        cache: Cache,
        network: NetworkInterface,
        graph: NetworkGraph,
        request_handler: RequestHandler,
    ):
        self.identity = identity
        self.cache = cache
        self.network = network
        self.graph = graph
        self.request_handler = request_handler
        self._processor = None
        
    def set_processor(self, processor: "ProcessorInterface"):
        self._processor = processor
        
    @property
    def handle(self):
        return self._processor.handle