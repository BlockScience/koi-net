from rid_lib.ext import Cache

from .log_system import LogSystem
from .assembler import NodeAssembler
from .config.core import NodeConfig
from .config.proxy import ConfigProxy
from .config.loader import ConfigLoader
from .processor.context import HandlerContext
from .effector import DerefHandler, Effector
from .handshaker import Handshaker
from .sync_manager import SyncManager
from .identity import NodeIdentity
from .workers import KnowledgeProcessingWorker, EventProcessingWorker
from .lifecycle import NodeLifecycle
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


class BaseNode(NodeAssembler):
    log_system: LogSystem = LogSystem
    kobj_queue: KobjQueue = KobjQueue
    event_queue: EventQueue = EventQueue
    poll_event_buf: EventBuffer = EventBuffer
    broadcast_event_buf: EventBuffer = EventBuffer
    config_schema = NodeConfig
    config: NodeConfig = ConfigProxy
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
    cache: Cache = lambda config: Cache(
        directory_path=config.koi_net.cache_directory_path)
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
    lifecycle: NodeLifecycle = NodeLifecycle

class FullNode(BaseNode):
    entrypoint: NodeServer = NodeServer

class PartialNode(BaseNode):
    entrypoint: NodePoller = NodePoller