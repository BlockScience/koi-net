import logging
from typing import Generic, TypeVar
from dependency_injector.providers import Factory, Self, Dependency, Callable, List, Object
from dependency_injector.containers import DeclarativeContainer

from rid_lib.ext import Cache

from koi_net.cache_adapter import CacheProvider

from .network.resolver import NetworkResolver
from .network.event_queue import NetworkEventQueue
from .network.graph import NetworkGraph
from .network.request_handler import RequestHandler
from .network.response_handler import ResponseHandler
from .network.error_handler import ErrorHandler
from .actor import Actor
from .processor.interface import ProcessorInterface
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
    
    config = Factory(
        NodeConfig.load_from_yaml
    )
    
    cache = Factory(
        CacheProvider, 
        config=config
    )
    
    identity = Factory(
        NodeIdentity, 
        config=config
    )
    
    # effector = Factory(
    #     Effector, 
    #     cache=cache,
    #     resolver=Self,
    #     processor=Self,
    #     action_context=Self
    # )
    
    graph = Factory(
        NetworkGraph, 
        cache=cache, 
        identity=identity
    )
    
    secure = Factory(
        Secure, 
        identity=identity, 
        cache=cache, 
        config=config
    )
    
    request_handler = Factory(
        RequestHandler, 
        cache=cache, 
        identity=identity, 
        secure=secure
    )
    
    response_handler = Factory(
        ResponseHandler, 
        cache=cache
    )
    
    resolver = Factory(
        NetworkResolver,
        config=config,
        cache=cache,
        identity=identity,
        graph=graph,
        request_handler=request_handler
    )

    event_queue = Factory(
        NetworkEventQueue,
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
    
    # action_context = Factory(
    #     ActionContext,
    #     identity=identity,
    #     cache=cache
    # )
    
    handler_context = Factory(
        HandlerContext,
        identity=identity,
        config=config,
        cache=cache,
        event_queue=event_queue,
        graph=graph,
        request_handler=request_handler,
        resolver=resolver
    )
    
    actor = Factory(
        Actor,
        ctx=handler_context
    )
    
    pipeline = Factory(
        KnowledgePipeline,
        handler_context=handler_context,
        cache=cache,
        request_handler=request_handler,
        event_queue=event_queue,
        graph=graph,
        default_handlers=knowledge_handlers
    )
    
    processor = Factory(
        ProcessorInterface,
        pipeline=pipeline,
        use_kobj_processor_thread=True # resolve this with to implementations?
    )
    
    error_handler = Factory(
        ErrorHandler,
        processor=processor,
        actor=actor
    )
    
    lifecycle = Factory(
        NodeLifecycle,
        config=config,
        identity=identity,
        graph=graph,
        processor=processor,
        cache=cache,
        actor=actor,
        use_kobj_processor_thread=True
    )
    
    server = Factory(
        NodeServer,
        config=config,
        lifecycle=lifecycle,
        secure=secure,
        processor=processor,
        event_queue=event_queue,
        response_handler=response_handler    
    )
    
    poller = Factory(
        NodePoller,
        processor=processor,
        lifecycle=lifecycle,
        resolver=resolver,
        config=config
    )