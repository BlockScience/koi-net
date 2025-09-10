from rid_lib.ext import Cache

from koi_net.network.resolver import NetworkResolver
from .config import NodeConfig
from .effector import Effector
from .network.graph import NetworkGraph
from .network.event_queue import NetworkEventQueue
from .network.request_handler import RequestHandler
from .identity import NodeIdentity
from .processor.interface import ProcessorInterface


class ActionContext:
    """Provides action handlers access to other subsystems."""
    
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
    """Provides knowledge handlers access to other subsystems."""
    
    identity: NodeIdentity
    config: NodeConfig
    cache: Cache
    event_queue: NetworkEventQueue
    graph: NetworkGraph
    request_handler: RequestHandler
    resolver: NetworkResolver
    effector: Effector
    _processor: ProcessorInterface | None
    
    def __init__(
        self,
        identity: NodeIdentity,
        config: NodeConfig,
        cache: Cache,
        event_queue: NetworkEventQueue,
        graph: NetworkGraph,
        request_handler: RequestHandler,
        resolver: NetworkResolver,
        effector: Effector
    ):
        self.identity = identity
        self.config = config
        self.cache = cache
        self.event_queue = event_queue
        self.graph = graph
        self.request_handler = request_handler
        self.resolver = resolver
        self.effector = effector
        self._processor = None
        
    def set_processor(self, processor: ProcessorInterface):
        self._processor = processor
        
    @property
    def handle(self):
        return self._processor.handle