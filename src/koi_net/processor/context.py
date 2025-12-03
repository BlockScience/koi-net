from typing import TYPE_CHECKING
from rid_lib.ext import Cache

from ..network.resolver import NetworkResolver
from ..config.core import NodeConfig
from ..config.loader import ConfigLoader
from ..network.graph import NetworkGraph
from ..network.event_queue import EventQueue
from ..network.request_handler import RequestHandler
from ..identity import NodeIdentity
from .kobj_queue import KobjQueue

if TYPE_CHECKING:
    from ..effector import Effector


class HandlerContext:
    """Context object provides knowledge handlers access to other components."""
    
    identity: NodeIdentity
    config: NodeConfig
    config_loader: ConfigLoader
    cache: Cache
    event_queue: EventQueue
    kobj_queue: KobjQueue
    graph: NetworkGraph
    request_handler: RequestHandler
    resolver: NetworkResolver
    effector: "Effector"
    
    def __init__(
        self,
        identity: NodeIdentity,
        config: NodeConfig,
        config_loader: ConfigLoader,
        cache: Cache,
        event_queue: EventQueue,
        kobj_queue: KobjQueue,
        graph: NetworkGraph,
        request_handler: RequestHandler,
        resolver: NetworkResolver
    ):
        self.identity = identity
        self.config = config
        self.config_loader = config_loader
        self.cache = cache
        self.event_queue = event_queue
        self.kobj_queue = kobj_queue
        self.graph = graph
        self.request_handler = request_handler
        self.resolver = resolver
    
    def set_effector(self, effector: "Effector"):
        """Post initialization injection of effector component."""
        self.effector = effector