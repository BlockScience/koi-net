
from koi_net.effector import Effector
from rid_lib.ext import Cache
from .network.graph import NetworkGraph
from .network.interface import NetworkInterface
from .network.request_handler import RequestHandler
from .identity import NodeIdentity
from .processor.interface import ProcessorInterface


class ActionContext:
    identity: NodeIdentity
    effector: Effector

    def __init__(
        self,
        identity: NodeIdentity,
        effector: Effector
    ):
        self.identity = identity
        self.effector = effector
    

class HandlerContext:
    identity: NodeIdentity
    cache: Cache
    network: NetworkInterface
    graph: NetworkGraph
    request_handler: RequestHandler
    effector: Effector
    _processor: ProcessorInterface | None
    
    def __init__(
        self,
        identity: NodeIdentity,
        cache: Cache,
        network: NetworkInterface,
        graph: NetworkGraph,
        request_handler: RequestHandler,
        effector: Effector
    ):
        self.identity = identity
        self.cache = cache
        self.network = network
        self.graph = graph
        self.request_handler = request_handler
        self.effector = effector
        self._processor = None
        
    def set_processor(self, processor: ProcessorInterface):
        self._processor = processor
        
    @property
    def handle(self):
        return self._processor.handle