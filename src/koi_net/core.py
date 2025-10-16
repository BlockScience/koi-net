from rid_lib.ext import Cache
from .assembler import NodeAssembler
from .config.base import BaseConfig
from .context import HandlerContext
from .effector import Effector
from .handshaker import Handshaker
from .identity import NodeIdentity
from .processor.kobj_worker import KnowledgeProcessingWorker
from .lifecycle import NodeLifecycle
from .network.error_handler import ErrorHandler
from .network.event_queue import EventQueue
from .network.graph import NetworkGraph
from .network.request_handler import RequestHandler
from .network.resolver import NetworkResolver
from .network.response_handler import ResponseHandler
from .network.poll_event_buffer import PollEventBuffer
from .poller import NodePoller
from .processor.handlers import (
    basic_manifest_handler, 
    basic_network_output_filter, 
    basic_rid_handler, 
    node_contact_handler, 
    edge_negotiation_handler, 
    forget_edge_on_node_deletion, 
    secure_profile_handler
)
from .processor.event_worker import EventProcessingWorker
from .processor.pipeline import KnowledgePipeline
from .processor.kobj_queue import KobjQueue
from .secure import Secure
from .server import NodeServer


# factory functions for components with non standard initializiation

def make_config() -> BaseConfig:
    return BaseConfig.load_from_yaml()

def make_cache(config: BaseConfig) -> Cache:
    return Cache(directory_path=config.koi_net.cache_directory_path)


class BaseNode(NodeAssembler):
    config = lambda: None
    kobj_queue = KobjQueue
    event_queue = EventQueue
    poll_event_buf = PollEventBuffer
    knowledge_handlers = lambda: [
        basic_rid_handler,
        basic_manifest_handler,
        secure_profile_handler,
        edge_negotiation_handler,
        node_contact_handler,
        basic_network_output_filter,
        forget_edge_on_node_deletion
    ]
    cache = make_cache
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