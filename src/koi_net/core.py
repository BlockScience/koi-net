from rid_lib.ext import Cache

from .config.loader import ConfigLoader
from .assembler import NodeAssembler
from .config.core import NodeConfig
from .processor.context import HandlerContext
from .effector import Effector
from .handshaker import Handshaker
from .identity import NodeIdentity
from .workers import KnowledgeProcessingWorker, EventProcessingWorker
from .lifecycle import NodeLifecycle
from .network.error_handler import ErrorHandler
from .network.event_queue import EventQueue
from .network.graph import NetworkGraph
from .network.request_handler import RequestHandler
from .network.resolver import NetworkResolver
from .network.response_handler import ResponseHandler
from .network.poll_event_buffer import PollEventBuffer
from .processor.pipeline import KnowledgePipeline
from .processor.kobj_queue import KobjQueue
from .secure import Secure
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
    config_cls = NodeConfig
    kobj_queue = KobjQueue
    event_queue = EventQueue
    poll_event_buf = PollEventBuffer
    config = ConfigLoader
    knowledge_handlers = [
        basic_rid_handler,
        basic_manifest_handler,
        secure_profile_handler,
        edge_negotiation_handler,
        node_contact_handler,
        basic_network_output_filter,
        forget_edge_on_node_deletion
    ]
    cache = lambda config: Cache(
        directory_path=config.koi_net.cache_directory_path)
    identity = NodeIdentity
    graph = NetworkGraph
    secure = Secure
    handshaker = Handshaker
    error_handler = ErrorHandler
    request_handler = RequestHandler
    response_handler = ResponseHandler
    resolver = NetworkResolver
    effector = Effector
    handler_context = HandlerContext
    pipeline = KnowledgePipeline
    kobj_worker = KnowledgeProcessingWorker
    event_worker = EventProcessingWorker
    lifecycle = NodeLifecycle

class FullNode(BaseNode):
    entrypoint = NodeServer

class PartialNode(BaseNode):
    entrypoint = NodePoller