from rid_lib.ext import Cache

from koi_net.effector import Effector
from koi_net.network.resolver import NetworkResolver
from .config import NodeConfig
from .network.graph import NetworkGraph
from .network.event_queue import EventQueue
from .network.request_handler import RequestHandler
from .identity import NodeIdentity
from .processor.kobj_queue import KobjQueue


class HandlerContext:
    """Provides knowledge handlers access to other subsystems."""
    
    identity: NodeIdentity
    config: NodeConfig
    cache: Cache
    event_queue: EventQueue
    kobj_queue: KobjQueue
    graph: NetworkGraph
    request_handler: RequestHandler
    resolver: NetworkResolver
    effector: Effector
    
    def __init__(
        self,
        identity: NodeIdentity,
        config: NodeConfig,
        cache: Cache,
        event_queue: EventQueue,
        kobj_queue: KobjQueue,
        graph: NetworkGraph,
        request_handler: RequestHandler,
        resolver: NetworkResolver,
        effector: Effector
    ):
        self.identity = identity
        self.config = config
        self.cache = cache
        self.event_queue = event_queue
        self.kobj_queue = kobj_queue
        self.graph = graph
        self.request_handler = request_handler
        self.resolver = resolver
        self.effector = effector