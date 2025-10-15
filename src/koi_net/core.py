from dataclasses import dataclass
from rid_lib.ext import Cache
from koi_net.config import NodeConfig
from koi_net.context import HandlerContext
from koi_net.effector import Effector
from koi_net.handshaker import Handshaker
from koi_net.identity import NodeIdentity
from koi_net.processor.handler import KnowledgeHandler
from koi_net.processor.kobj_worker import KnowledgeProcessingWorker
from koi_net.lifecycle import NodeLifecycle
from koi_net.network.error_handler import ErrorHandler
from koi_net.network.event_queue import EventQueue
from koi_net.network.graph import NetworkGraph
from koi_net.network.request_handler import RequestHandler
from koi_net.network.resolver import NetworkResolver
from koi_net.network.response_handler import ResponseHandler
from koi_net.network.poll_event_buffer import PollEventBuffer
from koi_net.poller import NodePoller
from koi_net.processor.handlers import (
    basic_manifest_handler, 
    basic_network_output_filter, 
    basic_rid_handler, 
    node_contact_handler, 
    edge_negotiation_handler, 
    forget_edge_on_node_deletion, 
    secure_profile_handler
)
from koi_net.processor.event_worker import EventProcessingWorker
from koi_net.processor.pipeline import KnowledgePipeline
from koi_net.processor.kobj_queue import KobjQueue
from koi_net.secure import Secure
from koi_net.server import NodeServer


@dataclass
class NodeContainer:
    poll_event_buf: PollEventBuffer
    kobj_queue: KobjQueue
    event_queue: EventQueue
    config: NodeConfig
    cache: Cache
    identity: NodeIdentity
    graph: NetworkGraph
    secure: Secure
    handshaker: Handshaker
    knowledge_handlers: list[KnowledgeHandler]
    request_handler: RequestHandler
    response_handler: ResponseHandler
    resolver: NetworkResolver
    effector: Effector
    handler_context: HandlerContext
    pipeline: KnowledgePipeline
    kobj_worker: KnowledgeProcessingWorker
    event_worker: EventProcessingWorker
    error_handler: ErrorHandler
    lifecycle: NodeLifecycle
    server: NodeServer
    # poller: NodePoller

class NodeAssembler:
    poll_event_buf = PollEventBuffer
    kobj_queue = KobjQueue
    event_queue = EventQueue
    config = NodeConfig
    cache = Cache
    identity = NodeIdentity
    graph = NetworkGraph
    secure = Secure
    handshaker = Handshaker
    request_handler = RequestHandler
    response_handler = ResponseHandler
    resolver = NetworkResolver
    knowledge_handlers = [
        basic_rid_handler,
        basic_manifest_handler,
        secure_profile_handler,
        edge_negotiation_handler,
        node_contact_handler,
        basic_network_output_filter,
        forget_edge_on_node_deletion
    ]
    handler_context = HandlerContext
    effector = Effector
    pipeline = KnowledgePipeline
    kobj_worker = KnowledgeProcessingWorker
    event_worker = EventProcessingWorker
    error_handler = ErrorHandler
    lifecycle = NodeLifecycle
    server = NodeServer
    poller = NodePoller
    
    @classmethod
    def create(cls) -> NodeContainer:
        # Layer 0
        config = cls.config.load_from_yaml()
        kobj_queue = cls.kobj_queue()
        event_queue = cls.event_queue()
        poll_event_buf = cls.poll_event_buf()
        
        # Layer 1
        cache = cls.cache(
            directory_path=config.koi_net.cache_directory_path
        )
        identity = cls.identity(
            config=config
        )
        
        # Layer 2
        graph = cls.graph(
            cache=cache,
            identity=identity
        )
        secure = cls.secure(
            identity=identity,
            cache=cache,
            config=config
        )
        handshaker = cls.handshaker(
            cache=cache,
            identity=identity,
            event_queue=event_queue
        )
        
        # Layer 3
        error_handler = cls.error_handler(
            kobj_queue=kobj_queue,
            handshaker=handshaker
        )
        
        # Layer 4
        request_handler = cls.request_handler(
            cache=cache,
            identity=identity,
            secure=secure,
            error_handler=error_handler
        )
        response_handler = cls.response_handler(
            cache=cache,
            kobj_queue=kobj_queue,
            poll_event_buf=poll_event_buf,
            secure=secure
        )
        
        # Layer 5
        resolver = cls.resolver(
            config=config,
            cache=cache,
            identity=identity,
            graph=graph,
            request_handler=request_handler
        )
        
        # Layer 6
        effector = cls.effector(
            cache=cache,
            resolver=resolver,
            kobj_queue=kobj_queue,
            identity=identity
        )
        
        # Layer 7
        handler_context = cls.handler_context(
            identity=identity,
            config=config,
            cache=cache,
            event_queue=event_queue,
            kobj_queue=kobj_queue,
            graph=graph,
            request_handler=request_handler,
            resolver=resolver,
            effector=effector
        )
        
        # Layer 8
        pipeline = cls.pipeline(
            handler_context=handler_context,
            cache=cache,
            request_handler=request_handler,
            event_queue=event_queue,
            graph=graph,
            knowledge_handlers=cls.knowledge_handlers
        )
        
        # Layer 9
        kobj_worker = cls.kobj_worker(
            kobj_queue=kobj_queue,
            pipeline=pipeline
        )
        event_worker = cls.event_worker(
            config=config,
            cache=cache,
            event_queue=event_queue,
            request_handler=request_handler,
            poll_event_buf=poll_event_buf
        )
        
        # Layer 10
        lifecycle = cls.lifecycle(
            config=config,
            identity=identity,
            graph=graph,
            kobj_queue=kobj_queue,
            kobj_worker=kobj_worker,
            event_queue=event_queue,
            event_worker=event_worker,
            cache=cache,
            handshaker=handshaker,
            request_handler=request_handler
        )
        
        # Layer 11
        server = cls.server(
            config=config,
            lifecycle=lifecycle,
            response_handler=response_handler
        )
        poller = cls.poller(
            kobj_queue=kobj_queue,
            lifecycle=lifecycle,
            resolver=resolver,
            config=config
        )
        
        return NodeContainer(
            poll_event_buf=poll_event_buf,
            kobj_queue=kobj_queue,
            event_queue=event_queue,
            config=config,
            cache=cache,
            identity=identity,
            graph=graph,
            secure=secure,
            request_handler=request_handler,
            response_handler=response_handler,
            resolver=resolver,
            effector=effector,
            handler_context=handler_context,
            pipeline=pipeline,
            kobj_worker=kobj_worker,
            event_worker=event_worker,
            error_handler=error_handler,
            lifecycle=lifecycle,
            server=server,
            poller=poller
        )