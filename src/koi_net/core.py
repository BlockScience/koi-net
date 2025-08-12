import logging
from typing import Generic, TypeVar
from rid_lib.ext import Cache
from .network.resolver import NetworkResolver
from .network.event_queue import NetworkEventQueue
from .network.graph import NetworkGraph
from .network.request_handler import RequestHandler
from .network.response_handler import ResponseHandler
from .network.error_handler import ErrorHandler
from .network.behavior import Actor
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


T = TypeVar("T", bound=NodeConfig)

class NodeInterface(Generic[T]):
    config: T
    cache: Cache
    identity: NodeIdentity
    resolver: NetworkResolver
    event_queue: NetworkEventQueue
    graph: NetworkGraph
    processor: ProcessorInterface
    secure: Secure
    server: NodeServer
    
    use_kobj_processor_thread: bool
    
    def __init__(
        self,
        config: T,
        use_kobj_processor_thread: bool = False,
        handlers: list[KnowledgeHandler] | None = None,
        cache: Cache | None = None,
        processor: ProcessorInterface | None = None
    ):
        self.config = config
        self.cache = cache or Cache(
            directory_path=self.config.koi_net.cache_directory_path
        )

        self.identity = NodeIdentity(config=self.config)
        self.effector = Effector(cache=self.cache)

        self.graph = NetworkGraph(
            cache=self.cache, 
            identity=self.identity
        )
        
        self.secure = Secure(
            identity=self.identity, 
            effector=self.effector, 
            config=self.config
        )
        
        self.request_handler = RequestHandler(
            effector=self.effector, 
            identity=self.identity,
            secure=self.secure
        )
        
        self.response_handler = ResponseHandler(self.cache, self.effector)
        
        self.resolver = NetworkResolver(
            config=self.config,
            cache=self.cache, 
            identity=self.identity,
            graph=self.graph,
            request_handler=self.request_handler,
            effector=self.effector
        )
        
        self.event_queue = NetworkEventQueue(
            config=self.config,
            cache=self.cache, 
            identity=self.identity,
            graph=self.graph,
            request_handler=self.request_handler,
            effector=self.effector
        )
        
        self.actor = Actor(
            identity=self.identity,
            effector=self.effector,
            event_queue=self.event_queue
        )
        
        # pull all handlers defined in default_handlers module
        if handlers is None:
            handlers = [
                obj for obj in vars(default_handlers).values() 
                if isinstance(obj, KnowledgeHandler)
            ]

        self.use_kobj_processor_thread = use_kobj_processor_thread
        
        self.action_context = ActionContext(
            identity=self.identity,
            effector=self.effector
        )
        
        self.handler_context = HandlerContext(
            identity=self.identity,
            cache=self.cache,
            event_queue=self.event_queue,
            graph=self.graph,
            request_handler=self.request_handler,
            effector=self.effector
        )
        
        self.pipeline = KnowledgePipeline(
            handler_context=self.handler_context,
            cache=self.cache,
            request_handler=self.request_handler,
            event_queue=self.event_queue,
            graph=self.graph,
            default_handlers=handlers
        )
        
        self.processor = processor or ProcessorInterface(
            pipeline=self.pipeline,
            use_kobj_processor_thread=self.use_kobj_processor_thread
        )
        
        self.error_handler = ErrorHandler(
            processor=self.processor,
            actor=self.actor
        )
        
        self.request_handler.set_error_handler(self.error_handler)
        
        self.handler_context.set_processor(self.processor)
        
        self.effector.set_processor(self.processor)
        self.effector.set_resolver(self.resolver)
        self.effector.set_action_context(self.action_context)
        
        self.lifecycle = NodeLifecycle(
            config=self.config,
            identity=self.identity,
            graph=self.graph,
            processor=self.processor,
            effector=self.effector,
            actor=self.actor,
            use_kobj_processor_thread=use_kobj_processor_thread
        )
        
        # if self.config.koi_net.node_profile.node_type == NodeType.FULL:
        self.server = NodeServer(
            config=self.config,
            lifecycle=self.lifecycle,
            secure=self.secure,
            processor=self.processor,
            event_queue=self.event_queue,
            response_handler=self.response_handler
        )
        
        self.poller = NodePoller(
            processor=self.processor,
            lifecycle=self.lifecycle,
            resolver=self.resolver,
            config=self.config
        )
