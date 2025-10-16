import inspect
from typing import Protocol
from dataclasses import make_dataclass

import structlog

from rid_lib.ext import Cache
from koi_net.config import NodeConfig
from koi_net.context import HandlerContext
from koi_net.core import NodeContainer
from koi_net.effector import Effector
from koi_net.handshaker import Handshaker
from koi_net.identity import NodeIdentity
from koi_net.interfaces.entrypoint import EntryPoint
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

log = structlog.stdlib.get_logger()


class BuildOrderer(type):
    def __new__(cls, name: str, bases: tuple, dct: dict[str]):
        cls = super().__new__(cls, name, bases, dct)
        
        def safe_update(d1: dict[str], d2: dict[str]):
            for k, v in d2.items():
                # excludes private and reserved attributes
                if not k.startswith("_"):
                    d1[k] = v
        
        if "_build_order" not in dct:
            components = {}
            for base in bases:
                # adds components from base classes
                safe_update(components, vars(base))
            
            # adds components from this class
            safe_update(components, dct)
            
            # recipe list constructed from names of non-None components
            cls._build_order = [
                name for name, _type in components.items()
                if _type is not None
            ]
            
        return cls


class NodeContainer(Protocol):
    entrypoint = EntryPoint

class NodeAssembler(metaclass=BuildOrderer):    
    def __new__(self) -> NodeContainer:
        return self._build()
    
    @classmethod
    def _build(cls) -> NodeContainer:
        components = {}
        for comp_name in cls._build_order:
            log.info(f"Assembling component '{comp_name}'")
            
            comp_factory = getattr(cls, comp_name, None)
            
            if comp_factory is None:
                log.error("Couldn't find factory for component")
                return
            
            sig = inspect.signature(comp_factory)
            
            required_comps = []
            for name, param in sig.parameters.items():
                required_comps.append((name, param.annotation))
            
            log.info(f"Component requires {[d[0] for d in required_comps]}")
            
            kwargs = {}
            for req_comp_name, req_comp_type in required_comps:
                comp = components.get(req_comp_name)
                if not comp:
                    log.error(f"failed to resolve dependency {req_comp_name}")
                    
                kwargs[req_comp_name] = comp
                
            components[comp_name] = comp_factory(**kwargs)
        
        NodeContainer = make_dataclass(
            cls_name="NodeContainer",
            fields=[
                (name, type(component)) 
                for name, component
                in components.items()
            ],
            frozen=True
        )
        
        return NodeContainer(**components)



def make_config() -> NodeConfig:
    return NodeConfig.load_from_yaml()

def make_cache(config: NodeConfig) -> Cache:
    return Cache(directory_path=config.koi_net.cache_directory_path)


class BaseNode(NodeAssembler):
    config = make_config
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
    server = NodeServer

class FullNode(BaseNode):
    entrypoint = NodeServer

class PartialNode(BaseNode):
    entrypoint = NodePoller


if __name__ == "__main__":
    print("Full Node:")
    for n, name in enumerate(FullNode._build_order):
        print(f"{n}. {name}")
    
    print("Partial Node:")
    for n, name in enumerate(PartialNode._build_order):
        print(f"{n}. {name}")
    
    partial_node = PartialNode()
    full_node = FullNode()