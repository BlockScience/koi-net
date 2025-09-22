import logging
from dependency_injector.providers import Factory, Callable, List, Object, Singleton
from dependency_injector.containers import DeclarativeContainer, WiringConfiguration

from rid_lib.ext import Cache

from koi_net.cache_adapter import CacheProvider
from koi_net.poll_event_buffer import PollEventBuffer
from koi_net.processor.event_worker import EventProcessingWorker
from koi_net.kobj_worker import KnowledgeProcessingWorker

from .network.resolver import NetworkResolver
from .network.event_queue import EventQueue
from .network.graph import NetworkGraph
from .network.request_handler import RequestHandler
from .network.response_handler import ResponseHandler
from .network.error_handler import ErrorHandler
from .processor.kobj_queue import KobjQueue
from .processor import default_handlers
from .processor.handler import KnowledgeHandler
from .processor.knowledge_pipeline import KnowledgePipeline
from .identity import NodeIdentity
from .secure import Secure
from .config import NodeConfig
from .context import HandlerContext, ActionContext
from .effector import Effector
from .server import NodeServer
from .lifecycle import NodeLifecycle
from .poller import NodePoller
from . import default_actions
from . import behaviors
from .behaviors import handshake_with, identify_coordinators, catch_up_with

logger = logging.getLogger(__name__)


# T = TypeVar("T", bound=NodeConfig)

class NodeContainer(DeclarativeContainer):
    """Interface for a node's subsystems.
    
    This class embodies a node, and wires up all of its subsystems to 
    work together. Currently, node implementations create an instance of
    this class and override behavior where needed. Most commonly this
    will be creating a new `Config` class, and adding additional knowledge
    handlers to the `pipeline`, but all subsystems may be overriden by
    passing new class implementations into `__init__`.
    """
    
    wiring_config = WiringConfiguration(
        modules=["koi_net.behaviors"]
    )
    
    poll_event_buf = Singleton(PollEventBuffer)

    kobj_queue = Singleton(KobjQueue)
    event_queue = Singleton(EventQueue)

    config = Singleton(
        NodeConfig.load_from_yaml
    )
    
    cache = Singleton(
        CacheProvider, 
        config=config
    )
    
    identity = Singleton(
        NodeIdentity, 
        config=config
    )
    
    # effector = Singleton(
    #     Effector, 
    #     cache=cache,
    #     resolver=Self,
    #     processor=Self,
    #     action_context=Self
    # )
    
    graph = Singleton(
        NetworkGraph, 
        cache=cache, 
        identity=identity
    )
    
    secure = Singleton(
        Secure, 
        identity=identity, 
        cache=cache, 
        config=config
    )
    
    request_handler = Singleton(
        RequestHandler, 
        cache=cache, 
        identity=identity, 
        secure=secure
    )
    
    response_handler = Singleton(
        ResponseHandler, 
        cache=cache
    )
    
    resolver = Singleton(
        NetworkResolver,
        config=config,
        cache=cache,
        identity=identity,
        graph=graph,
        request_handler=request_handler
    )
    
    knowledge_handlers = List(
        Object(default_handlers.basic_rid_handler),
        Object(default_handlers.basic_manifest_handler),
        Object(default_handlers.secure_profile_handler),
        Object(default_handlers.edge_negotiation_handler),
        Object(default_handlers.coordinator_contact),
        Object(default_handlers.basic_network_output_filter),
        Object(default_handlers.forget_edge_on_node_deletion)
    )
    
    # action_context = Singleton(
    #     ActionContext,
    #     identity=identity,
    #     cache=cache
    # )
    
    handler_context = Singleton(
        HandlerContext,
        identity=identity,
        config=config,
        cache=cache,
        event_queue=event_queue,
        graph=graph,
        request_handler=request_handler,
        resolver=resolver
    )
    
    # actor = Singleton(
    #     Actor,
    #     ctx=handler_context
    # )
    
    pipeline = Singleton(
        KnowledgePipeline,
        handler_context=handler_context,
        cache=cache,
        request_handler=request_handler,
        event_queue=event_queue,
        graph=graph,
        default_handlers=knowledge_handlers
    )
    
    kobj_worker = Singleton(
        KnowledgeProcessingWorker,
        kobj_queue=kobj_queue,
        pipeline=pipeline
    )
    
    event_worker = Singleton(
        EventProcessingWorker,
        config=config,
        cache=cache,
        event_queue=event_queue,
        request_handler=request_handler,
        poll_event_buf=poll_event_buf
    )
    
    handshake_with = Callable(
        handshake_with,
        cache=cache,
        identity=identity,
        event_queue=event_queue
    )
    
    identify_coordinators = Callable(
        identify_coordinators,
        resolver=resolver
    )
    
    catch_up_with = Callable(
        catch_up_with,
        request_handler=request_handler,
        identity=identity,
        kobj_queue=kobj_queue
    )
    
    error_handler = Singleton(
        ErrorHandler,
        kobj_queue=kobj_queue,
        handshake_with=handshake_with
    )
    
    lifecycle = Singleton(
        NodeLifecycle,
        config=config,
        identity=identity,
        graph=graph,
        kobj_queue=kobj_queue,
        kobj_worker=kobj_worker,
        event_queue=event_queue,
        event_worker=event_worker,
        cache=cache,
        handshake_with=handshake_with,
        catch_up_with=catch_up_with,
        identify_coordinators=identify_coordinators
    )
    
    server = Singleton(
        NodeServer,
        config=config,
        lifecycle=lifecycle,
        secure=secure,
        kobj_queue=kobj_queue,
        response_handler=response_handler,
        poll_event_buf=poll_event_buf
    )
    
    poller = Singleton(
        NodePoller,
        kobj_queue=kobj_queue,
        lifecycle=lifecycle,
        resolver=resolver,
        config=config
    )