import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable
from rid_lib.core import RID, RIDType
from rid_lib.ext import Bundle, Cache, Manifest

from koi_net.reference import NodeReference
from ..network import NetworkInterface
from ..protocol.event import Event, EventType

logger = logging.getLogger(__name__)

type InternalEventType = EventType | None


class InternalEvent(Event):
    event_type: InternalEventType = None
    normalized_event_type: InternalEventType = None
   
    def normalized_event(self) -> Event:
        if self.normalized_event_type is None:
            raise ValueError("InternalEvent with normalized_event_type set to 'None' cannot be converted to an event")
        
        return Event(
            rid=self.rid,
            event_type=self.normalized_event_type,
            manifest=self.manifest,
            contents=self.contents
        )


class HandlerType(StrEnum):
    RID = "rid", # guaranteed RID - decides whether to delete from cache OR validate manifest
    Manifest = "manifest", # guaranteed RID, Manifest - decides whether to validate bundle
    Bundle = "bundle", # guaranteed RID, Manifest, contents - decides whether to write to cache
    Network = "network", # occurs after cache action - decides whether to handle network
    Final = "final" # occurs after network.push - final action

type HandlerFunc = Callable[["ProcessorInterface", InternalEvent], InternalEvent | None]

@dataclass
class Handler:
    func: HandlerFunc
    handler_type: HandlerType
    rid_types: list[RIDType] | None


class ProcessorInterface:
    def __init__(
        self, 
        cache: Cache, 
        network: NetworkInterface,
        my: NodeReference,
        default_handlers: list[Handler] = []
    ):
        self.cache = cache
        self.network = network
        self.my = my
        self.handlers: list[Handler] = default_handlers
    
    @classmethod
    def as_handler(
        cls,
        handler_type: HandlerType,
        rid_types: list[RIDType] | None = None
    ):
        """Special decorator that returns a Handler instead of a function."""
        def decorator(func: HandlerFunc) -> Handler:
            handler = Handler(func, handler_type, rid_types, )
            return handler
        return decorator
            
    def register_handler(
        self,
        handler_type: HandlerType,
        rid_types: list[RIDType] | None = None
    ):
        """Assigns decorated function as handler for this Processor."""
        def decorator(func: HandlerFunc) -> HandlerFunc:
            handler = Handler(func, handler_type, rid_types)
            self.handlers.append(handler)
            return func
        return decorator
            
    def call_handler_chain(
        self, 
        handler_type: HandlerType,
        ievent: InternalEvent
    ):
        for handler in reversed(self.handlers):
            if handler_type != handler.handler_type: 
                continue
            
            if handler.rid_types and type(ievent.rid) not in handler.rid_types:
                continue
            
            logger.info(f"Calling {handler_type} handler '{handler.func.__name__}'")
            ievent = handler.func(self, ievent)
            if not ievent: 
                logger.info(f"Handler chain '{handler_type}' broken")
                return
        return ievent

        
    def handle_ievent(self, ievent: InternalEvent):
        logger.info(f"Started handling internal event for '{ievent.rid}'")
        ievent = self.call_handler_chain(HandlerType.RID, ievent)
        if not ievent: return
        
        if ievent.event_type == EventType.FORGET:
            logger.info(f"Deleting '{ievent.rid}' from cache")
            self.cache.delete(ievent.rid)
                    
        else:
            # attempt to retrieve manifest
            if not ievent.manifest:
                logger.info("Manifest not found, attempting to fetch")
                remote_manifest = self.network.fetch_remote_manifest(ievent.rid)
                if not remote_manifest: return
                ievent.manifest = remote_manifest
            
            ievent = self.call_handler_chain(HandlerType.Manifest, ievent)
            if not ievent: return
            
            # attempt to retrieve bundle
            if not ievent.bundle:
                logger.info("Bundle not found, attempting to fetch")
                remote_bundle = self.network.fetch_remote_bundle(ievent.rid)
                if not remote_bundle: return
                # TODO: WARNING MANIFEST MAY BE DIFFERENT
                ievent.manifest = remote_bundle.manifest
                ievent.contents = remote_bundle.contents
                
            ievent = self.call_handler_chain(HandlerType.Bundle, ievent)
            if not ievent: return
            # cache operation
            logger.info(f"Writing '{ievent.rid}' to cache")
            self.cache.write(ievent.bundle)
            
        ievent = self.call_handler_chain(HandlerType.Network, ievent)
        if not ievent: return

        logger.info(f"Pushing event {ievent.normalized_event_type} '{ievent.rid}' to network")
        self.network.push_event(ievent.normalized_event())
        ievent = self.call_handler_chain(HandlerType.Final, ievent)
        
    
    def handle_rid(self, rid: RID, event_type: InternalEventType = None):
        logger.info(f"Handling RID '{rid}', event type: {event_type}")
        ievent = InternalEvent(
            rid=rid, 
            event_type=event_type
        )
        self.handle_ievent(ievent)
    
    def handle_manifest(self, manifest: Manifest, event_type: InternalEventType = None):
        logger.info(f"Handling Manifest '{manifest.rid}', event type: {event_type}")
        ievent = InternalEvent(
            rid=manifest.rid, 
            manifest=manifest, 
            event_type=event_type
        )
        self.handle_ievent(ievent)
    
    def handle_bundle(self, bundle: Bundle, event_type: InternalEventType = None):
        logger.info(f"Handling Bundle '{bundle.rid}', event type: {event_type}")
        ievent = InternalEvent(
            rid=bundle.rid, 
            manifest=bundle.manifest, 
            contents=bundle.contents, 
            event_type=event_type
        )
        self.handle_ievent(ievent)
        
    def handle_event(self, event: Event):
        logger.info(f"Handling Event '{event.rid}, event type: {event.event_type}")
        ievent = InternalEvent(
            rid=event.rid,
            manifest=event.manifest,
            contents=event.contents,
            event_type=event.event_type
        )
        self.handle_ievent(ievent)
