import httpx
from rid_lib.ext import Event, Bundle
from rid_lib.ext.event import EventType
from rid_lib.ext.manifest import Manifest

from koi_net import Edge, EventArray, Node
from rid_types import KoiNetEdge, KoiNetNode
from .config import this_node_rid, this_node_profile
from .core import cache


def handle_incoming_event(event: Event):
    if event.rid.context == KoiNetEdge.context:
        handle_incoming_edge_event(event)
    elif event.rid.context == KoiNetNode.context:
        ...
        
        
def handle_incoming_edge_event(event: Event):
    if event.bundle is None or event.bundle.contents is None:
        # TODO: state transfer from event source
        return
    
    edge_profile = Edge(**event.bundle.contents)
    # indicates peer subscriber
    if edge_profile.source == this_node_rid:
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return
        
        if any(context not in this_node_profile.provides.event for context in edge_profile.contexts):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            ...
        
        # approve edge profile
        edge_profile.status = "approved"
        updated_edge_bundle = Bundle.generate(event.rid, event.bundle.contents)
        cache.write(updated_edge_bundle)
        
        # forward to subscriber
        target_node_bundle = cache.read(edge_profile.target)
        if target_node_bundle is None:
            # TODO: handle unknown subscriber node (delete edge?)
            ...
        target_node_profile = Node(**target_node_bundle.contents)
        
        event = Event(
            rid=event.rid,
            event_type=EventType.UPDATE,
            bundle=updated_edge_bundle
        )
        events_json = EventArray([event]).model_dump_json()
        
        # TODO: broadcast event to subscriber
    
    # indiciates peer provider
    elif edge_profile.target == this_node_rid:
        ...
    
    # edge regarding third party nodes, handle as sensor
    else:
        ...
        
    # cache.write()
    
def handle_outgoing_event(event: Event):    
    ...
    

