from koi_net.build.base import BaseAssembly
from .log_system import LogSystem
from .cache import Cache
from .config.base import BaseNodeConfig
from .config.proxy import ConfigProxy
from .config.loader import ConfigLoader
from .config.full_node import FullNodeConfig
from .config.partial_node import PartialNodeConfig
from .processor.context import HandlerContext
from .effector import DerefHandler, Effector
from .behaviors.handshaker import Handshaker
from .behaviors.sync_manager import SyncManager
from .identity import NodeIdentity
from .workers import KnowledgeProcessingWorker, EventProcessingWorker
from .network.error_handler import ErrorHandler
from .network.event_queue import EventQueue
from .network.graph import NetworkGraph
from .network.request_handler import RequestHandler
from .network.resolver import NetworkResolver
from .network.response_handler import ResponseHandler
from .network.event_buffer import EventBuffer
from .processor.pipeline import KnowledgePipeline
from .processor.kobj_queue import KobjQueue
from .processor.handler import KnowledgeHandler
from .secure_manager import SecureManager
from .behaviors.profile_monitor import ProfileMonitor
from .entrypoints import NodeServer, NodePoller
from .processor.knowledge_handlers import (
    basic_manifest_handler, 
    basic_network_output_filter, 
    basic_rid_handler, 
    node_contact_handler, 
    edge_negotiation_handler, 
    forget_edge_on_node_deletion, 
    secure_profile_handler
)

class BaseNode(BaseAssembly):
    _log_system: LogSystem = LogSystem
    kobj_queue: KobjQueue = KobjQueue
    event_queue: EventQueue = EventQueue
    poll_event_buf: EventBuffer = EventBuffer
    broadcast_event_buf: EventBuffer = EventBuffer
    config_schema = BaseNodeConfig
    config: BaseNodeConfig = ConfigProxy
    config_loader: ConfigLoader = ConfigLoader
    knowledge_handlers: list[KnowledgeHandler] = [
        basic_rid_handler,
        basic_manifest_handler,
        secure_profile_handler,
        edge_negotiation_handler,
        node_contact_handler,
        basic_network_output_filter,
        forget_edge_on_node_deletion
    ]
    deref_handlers: list[DerefHandler] = []
    cache: Cache = Cache
    identity: NodeIdentity = NodeIdentity
    graph: NetworkGraph = NetworkGraph
    secure_manager: SecureManager = SecureManager
    handshaker: Handshaker = Handshaker
    error_handler: ErrorHandler = ErrorHandler
    request_handler: RequestHandler = RequestHandler
    sync_manager: SyncManager = SyncManager
    response_handler: ResponseHandler = ResponseHandler
    resolver: NetworkResolver = NetworkResolver
    handler_context: HandlerContext = HandlerContext
    effector: Effector = Effector
    pipeline: KnowledgePipeline = KnowledgePipeline
    kobj_worker: KnowledgeProcessingWorker = KnowledgeProcessingWorker
    event_worker: EventProcessingWorker = EventProcessingWorker
    profile_monitor: ProfileMonitor = ProfileMonitor
    
    def __new__(cls, *args, **kwargs):
        cls._log_system(*args, **kwargs)
        return super().__new__(cls, *args, **kwargs)

class FullNode(BaseNode):
    server: NodeServer = NodeServer
    config: FullNodeConfig

class PartialNode(BaseNode):
    poller: NodePoller = NodePoller
    config: PartialNodeConfig