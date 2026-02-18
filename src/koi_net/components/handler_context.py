from logging import Logger
from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from rid_lib.ext import Cache

from .resolver import NetworkResolver
from ..config.base import BaseNodeConfig
from ..config.provider import ConfigProvider
from .graph import NetworkGraph
from .event_queue import EventQueue
from .request_handler import RequestHandler
from .identity import NodeIdentity
from .kobj_queue import KobjQueue

if TYPE_CHECKING:
    from .effector import Effector


@dataclass
class HandlerContext:
    """Context object provides knowledge handlers access to other components."""
    
    log: Logger
    identity: NodeIdentity
    config: ConfigProvider | BaseNodeConfig
    cache: Cache
    event_queue: EventQueue
    kobj_queue: KobjQueue
    graph: NetworkGraph
    request_handler: RequestHandler
    resolver: NetworkResolver
    effector: "Effector" = field(init=False)
    
    def set_effector(self, effector: "Effector"):
        """Post initialization injection of effector component."""
        self.effector = effector