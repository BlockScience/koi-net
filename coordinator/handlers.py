from coordinator.processor import HandlerType
from koi_net import EdgeModel
from rid_types import KoiNetNode, KoiNetEdge
from rid_lib.ext import Event, EventType, Bundle
from .core import processor, network, cache

@processor.register_handler(
    contexts=[KoiNetNode.context],
    handler_type=HandlerType.EVENT
)
def handshake_handler(event: Event, event_type: EventType | None):
    print("trigger handshake handler")
    # only respond if node is unknown to me
    if event_type != EventType.NEW: return
    
    my_bundle = cache.read(network.me)
    
    network.push_event_to(
        event=Event.from_bundle(EventType.NEW, my_bundle),
        node=event.rid,
        flush=True
    )
    
    edge_bundle = Bundle.generate(
        KoiNetEdge("partial->coordinator"),
        EdgeModel(
            source=event.rid,
            target=network.me,
            comm_type="webhook",
            contexts=[
                KoiNetNode.context,
                KoiNetEdge.context
            ],
            status="proposed"
        ).model_dump()
    )
        
    print(edge_bundle)
    
    processor.handle_state(edge_bundle)
    
    network.push_event_to(
        event=Event.from_bundle(EventType.NEW, edge_bundle),
        node=event.rid,
        flush=True
    )
    
@processor.register_handler(
    contexts=[KoiNetEdge.context],
    handler_type=HandlerType.EVENT
)
def edge_negotiation_handler(event: Event, event_type: EventType):
    print("trigger negotiation handler")
    bundle = event.bundle or cache.read(event.rid)
    edge_profile = EdgeModel(**bundle.contents)

    # indicates peer subscriber
    if edge_profile.source == network.me:
        edge_profile = EdgeModel(**bundle.contents)
        
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return
        
        if any(context not in network.state.get_node(network.me).provides.event for context in edge_profile.contexts):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            print("requested context not provided")
            return
            
        if not cache.read(edge_profile.target):
            # TODO: handle unknown subscriber node (delete edge?)
            print("unknown subscriber")
            return
        
        # approve edge profile
        edge_profile.status = "approved"
        updated_bundle = Bundle.generate(bundle.manifest.rid, edge_profile.model_dump())
        
        event = Event.from_bundle(EventType.UPDATE, updated_bundle)
        
        network.push_event_to(event, edge_profile.target, flush=True)
        # self.network.flush_webhook_queue(edge_profile.target)
        processor.handle_event(event)
        
    elif edge_profile.target == network.me:
        print("other node approved my edge!")