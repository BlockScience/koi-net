from koi_net.models import EdgeModel, NormalizedType
from koi_net.rid_types import KoiNetNode, KoiNetEdge
from rid_lib.ext import Event, EventType, Bundle
from .core import node, this_node_profile


@node.processor.register_event_handler(contexts=[KoiNetNode])
def handshake_handler(event: Event, event_type: NormalizedType):
    print("trigger handshake handler")
    # only respond if node is unknown to me
    if event_type != EventType.NEW: return
    
    my_bundle = node.cache.read(node.network.me)
    
    node.network.push_event_to(
        event=Event.from_bundle(EventType.NEW, my_bundle),
        node=event.rid,
        flush=True
    )
    
    edge_bundle = Bundle.generate(
        KoiNetEdge("partial->coordinator"),
        EdgeModel(
            source=event.rid,
            target=node.network.me,
            comm_type="webhook",
            rid_types=[KoiNetNode, KoiNetEdge],
            status="proposed"
        ).model_dump()
    )
        
    print(edge_bundle)
    
    node.processor.handle_state(edge_bundle)
    
    node.network.push_event_to(
        event=Event.from_bundle(EventType.NEW, edge_bundle),
        node=event.rid,
        flush=True
    )
    
@node.processor.register_event_handler(contexts=[KoiNetEdge])
def edge_negotiation_handler(event: Event, event_type: NormalizedType):
    print("trigger negotiation handler")
    bundle = event.bundle or node.cache.read(event.rid)
    edge_profile = EdgeModel(**bundle.contents)

    # indicates peer subscriber
    if edge_profile.source == node.network.me:
        edge_profile = EdgeModel(**bundle.contents)
        
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return
        
        if any(context not in this_node_profile.provides.event for context in edge_profile.rid_types):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            print("requested context not provided")
            return
            
        if not node.cache.read(edge_profile.target):
            # TODO: handle unknown subscriber node (delete edge?)
            print("unknown subscriber")
            return
        
        # approve edge profile
        edge_profile.status = "approved"
        updated_bundle = Bundle.generate(bundle.manifest.rid, edge_profile.model_dump())
        
        event = Event.from_bundle(EventType.UPDATE, updated_bundle)
        
        node.network.push_event_to(event, edge_profile.target, flush=True)
        # self.network.flush_webhook_queue(edge_profile.target)
        node.processor.handle_event(event)
        
    elif edge_profile.target == node.network.me:
        print("other node approved my edge!")