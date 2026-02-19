from pathlib import Path

from .build.base import BaseAssembly
from .log_system import LogSystem
from .config.base import BaseNodeConfig
from .config.provider import ConfigProvider
from .config.full_node import FullNodeConfig
from .config.partial_node import PartialNodeConfig

from .components import (
    Cache,
    Effector,
    Handshaker,
    SyncManager,
    PortManager,
    NodeIdentity,
    KnowledgeProcessingWorker, 
    EventProcessingWorker,
    ErrorHandler,
    EventQueue,
    NetworkGraph,
    RequestHandler,
    NetworkResolver,
    ResponseHandler,
    EventBuffer,
    KnowledgePipeline,
    KobjQueue,
    SecureManager,
    ProfileMonitor,
    NodeServer, 
    NodePoller,
    BasicManifestHandler,
    BasicNetworkOutputFilter,
    BasicRidHandler,
    ForgetNodeHandler,
    NodeContactHandler,
    EdgeNegotiationHandler,
    SecureProfileHandler
)

class BaseNode(BaseAssembly):
    _log_system: LogSystem = LogSystem
    kobj_queue: KobjQueue = KobjQueue
    event_queue: EventQueue = EventQueue
    poll_event_buf: EventBuffer = EventBuffer
    broadcast_event_buf: EventBuffer = EventBuffer
    config_schema = BaseNodeConfig
    config: ConfigProvider | BaseNodeConfig = ConfigProvider
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
    effector: Effector = Effector
    pipeline: KnowledgePipeline = KnowledgePipeline
    kobj_worker: KnowledgeProcessingWorker = KnowledgeProcessingWorker
    event_worker: EventProcessingWorker = EventProcessingWorker
    profile_monitor: ProfileMonitor = ProfileMonitor
    
    # knowledge handlers
    
    basic_manifest_handler: BasicManifestHandler = BasicManifestHandler
    basic_network_output_filter: BasicNetworkOutputFilter = BasicNetworkOutputFilter
    basic_rid_handler: BasicRidHandler = BasicRidHandler
    forget_node_handler: ForgetNodeHandler = ForgetNodeHandler
    node_contact_handler: NodeContactHandler = NodeContactHandler
    edge_negotiation_handler: EdgeNegotiationHandler = EdgeNegotiationHandler
    secure_profile_handler: SecureProfileHandler = SecureProfileHandler
    
    def __new__(cls, *args, root_dir: Path = Path.cwd(), **kwargs):
        cls._log_system()
        return super().__new__(cls, *args, root_dir=root_dir, **kwargs)

class FullNode(BaseNode):
    config: FullNodeConfig
    port_manager: PortManager = PortManager
    server: NodeServer = NodeServer

class PartialNode(BaseNode):
    config: PartialNodeConfig
    poller: NodePoller = NodePoller
