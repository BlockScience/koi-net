from rid_lib.ext import Event, Bundle
from rid_lib.ext.cache import Cache
from rid_lib.ext.event import EventType

from .network_interface import NetworkInterface
from koi_net import EdgeModel
from koi_net.rid_types import KoiNetEdge, KoiNetNode
from .config import this_node_rid, this_node_profile


class KnowledgeProcessor:
    def __init__(self, cache: Cache, network: NetworkInterface):
        self.cache = cache
        self.network = network
        self.allowed_contexts = [
            KoiNetNode.context,
            KoiNetEdge.context
        ]
        
    def route_event(self, event: Event):
        self.handle_event(event)
        
        if event.rid.context == KoiNetEdge.context:
            bundle = event.bundle or self.cache.read(event.rid)
            edge_profile = EdgeModel(**bundle.contents)
        
            # indicates peer subscriber
            if edge_profile.source == this_node_rid:
                bundle = self.handle_edge_negotiation(bundle)            
            
    
    def handle_event(self, event: Event):
        print("handling event:", event.event_type, event.rid)
        if event.rid.context not in self.allowed_contexts:
            print("ignoring disallowed context")
            return None
        
        if event.event_type in (EventType.NEW, EventType.UPDATE):
            if event.bundle is None:
                print("bundle not attached")
                # TODO: retrieve bundle
                return None
            
            self.handle_state(event.bundle)
        elif event.event_type == EventType.FORGET:
            print("deleting", event.rid, "from cache")
            self.cache.delete(event.rid)
            self.network.push_event(event, flush=True)    
    
    def handle_state(self, bundle: Bundle):
        internal_type = None
        print("handling state:", bundle.manifest.rid)
        if self.cache.exists(bundle.manifest.rid):
            print("RID known to cache")
            prev_bundle = self.cache.read(bundle.manifest.rid)

            if bundle.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
                print("no change in knowledge, ignoring")
                return None # same knowledge
            if bundle.manifest.timestamp <= prev_bundle.manifest.timestamp:
                print("older manifest, ignoring")
                return None # incoming state is older
            
            print("newer manifest")
            print("writing", bundle.manifest.rid, "to cache")
            self.cache.write(bundle)
            internal_type = EventType.UPDATE

        else:
            print("RID unknown to cache")
            print("writing", bundle.manifest.rid, "to cache")
            self.cache.write(bundle)
            internal_type = EventType.NEW
        
        if bundle.manifest.rid.context in (KoiNetNode.context, KoiNetEdge.context):
            self.network.state.generate()
        
        self.network.push_event(
            Event(
                rid=bundle.manifest.rid,
                event_type=internal_type,
                bundle=bundle
            ),
            flush=True
        )
        
    def handle_edge_negotiation(self, bundle: Bundle):
        edge_profile = EdgeModel(**bundle.contents)
        
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return
        
        if any(context not in this_node_profile.provides.event for context in edge_profile.contexts):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            print("requested context not provided")
            return
            
        if not self.cache.read(edge_profile.target):
            # TODO: handle unknown subscriber node (delete edge?)
            print("unknown subscriber")
            return
        
        # approve edge profile
        edge_profile.status = "approved"
        updated_bundle = Bundle.generate(bundle.manifest.rid, edge_profile.model_dump())
        
        event = Event(
            rid=bundle.manifest.rid,
            event_type=EventType.UPDATE,
            bundle=updated_bundle
        )
        
        self.network.push_event_to(event, edge_profile.target, flush=True)
        # self.network.flush_webhook_queue(edge_profile.target)
        self.handle_event(event)


