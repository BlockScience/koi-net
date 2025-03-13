import networkx as nx
import httpx
from rid_lib import RID
from rid_lib.ext.cache import Cache
from rid_lib.ext.event import Event
from koi_net import EdgeModel, EventArrayModel, EventQueueModel, KoiNetPath, NodeModel, NodeType, ManifestArrayModel, RIDArrayModel, BundleArrayModel
from koi_net.rid_types import KoiNetEdge, KoiNetNode
from .config import this_node_rid
from queue import Queue
from .network_models import *


class NetworkState:
    def __init__(self, cache: Cache):
        self.cache = cache
        self.dg = nx.DiGraph()
        self.generate()
        
    def generate(self):
        print("generating network state...")
        self.dg.clear()
        for rid in self.cache.read_all_rids():
            if rid.context == KoiNetNode.context:
                node_bundle = self.cache.read(rid)
                
                self.dg.add_node(
                    str(rid),
                    **node_bundle.contents
                )
                
            elif rid.context == KoiNetEdge.context:
                edge_bundle = self.cache.read(rid)
                edge = EdgeModel(**edge_bundle.contents)
                
                self.dg.add_edge(
                    str(edge.source),
                    str(edge.target),
                    **edge_bundle.contents
                )
        
    def get_sub_rids(self, context: str | None = None):
        potential_sub_rids = self.dg.successors(str(this_node_rid))
        subscribers = []
        for sub_rid in potential_sub_rids:
            edge_profile = EdgeModel(**self.dg.edges[str(this_node_rid), sub_rid])
            if edge_profile.status != "approved": continue
            if context and (context not in edge_profile.contexts): continue
            subscribers.append(RID.from_string(sub_rid))
        return subscribers
            
    def get_node(self, node: RID):
        node_contents = self.dg.nodes.get(str(node))
        if node_contents:
            return NodeModel(**node_contents)



class NetworkAdapter:
    def __init__(self, state: NetworkState):
        self.state = state
    
    def handshake(self, url, bundle):        
        resp = httpx.post(
            url=url + KoiNetPath.HANDSHAKE,
            data=bundle.model_dump_json()
        )
        return Bundle.model_validate(resp.json())
    
    def broadcast_events(self, node: RID, events):
        node_profile = self.state.get_node(node)
                
        httpx.post(
            url=node_profile.base_url + KoiNetPath.EVENTS_BROADCAST,
            data=EventArrayModel(events).model_dump_json()
        )
    
    def retrieve_rids(self, node: RID, **kwargs):
        node_profile = self.state.get_node(node)
        
        resp = httpx.post(
            url=node_profile.base_url + KoiNetPath.STATE_RIDS,
            data=RetrieveRids(**kwargs).model_dump_json()
        )
        
        return RIDArrayModel.model_validate(resp.json()).root
        
        
    def retrieve_manifests(self, node: RID, **kwargs):
        node_profile = self.state.get_node(node)
        
        resp = httpx.post(
            url=node_profile.base_url + KoiNetPath.STATE_MANIFESTS,
            data=RetrieveManifests(**kwargs).model_dump_json()
        )
        
        return ManifestArrayModel.model_validate(resp.json()).root
        
    def retrieve_bundles(self, node: RID, **kwargs):
        node_profile = self.state.get_node(node)
        
        resp = httpx.post(
            url=node_profile.base_url + KoiNetPath.STATE_BUNDLES,
            data=RetrieveBundles(**kwargs).model_dump_json()
        )
        
        return BundleArrayModel.model_validate(resp.json()).root
        

class NetworkInterface:
    def __init__(self, file_path, cache: Cache):
        print('CREATED A NEW NETWORK INTERFACE')
        self.state = NetworkState(cache)
        self.adapter = NetworkAdapter(self.state)
        self.event_queues_file_path = file_path
        
        self.poll_event_queue: dict[RID, Queue] = dict()
        self.webhook_event_queue: dict[RID, Queue] = dict()
        self.load_queues()
    
    def load_queues(self):
        print("LOADED QUEUES")
        try:
            with open(self.event_queues_file_path, "r") as f:
                queues = EventQueueModel.model_validate_json(f.read())
            
            for node in queues.poll.keys():
                for event in queues.poll[node]:
                    queue = self.poll_event_queue.setdefault(node, Queue())
                    queue.put(event)
            
            for node in queues.webhook.keys():
                for event in queues.webhook[node]:
                    queue = self.webhook_event_queue.setdefault(node, Queue())
                    queue.put(event)
                    
            print(self.poll_event_queue)
            
        except FileNotFoundError:
            return
        
    def save_queues(self):
        events_model = EventQueueModel(
            poll={
                node: list(queue.queue) 
                for node, queue in self.poll_event_queue.items()
                if not queue.empty()
            },
            webhook={
                node: list(queue.queue) 
                for node, queue in self.webhook_event_queue.items()
                if not queue.empty()
            }
        )
                
        with open(self.event_queues_file_path, "w") as f:
            f.write(events_model.model_dump_json(indent=2))
            
                
    
    def push_event(self, event: Event, flush=False):
        subs = self.state.get_sub_rids(event.rid.context)
        for sub in subs:
            self.push_event_to(event, sub, flush)
                
    def push_event_to(self, event: Event, node: RID, flush=False):
        if not isinstance(node, RID):
            raise Exception("node must be of type RID")
        print(repr(node))
        print("pushing event", event.event_type, event.rid, "to", node)
        node_profile = self.state.get_node(node)
        if not node_profile:
            raise Exception("unknown node", node)
        
        # select queue from node type
        if node_profile.node_type == NodeType.FULL:
            event_queue = self.webhook_event_queue
        elif node_profile.node_type == NodeType.PARTIAL:
            event_queue = self.poll_event_queue
        
        queue = event_queue.setdefault(node, Queue())
        print(queue)
        queue.put(event)
        
        print("queue size:", queue.qsize(), node_profile.node_type)
        
        if flush:
            self.flush_webhook_queue(node)
    
    def flush_poll_queue(self, node: RID) -> list[Event]:
        queue = self.poll_event_queue.get(node)
        print(queue)
        print("flushing poll queue, size:", queue.qsize())
        events = list()
        if queue:
            while not queue.empty():
                events.append(queue.get())
        
        print("got", len(events), "items")
        
        return events
    
    def flush_webhook_queue(self, node: RID):
        node_profile = self.state.get_node(node)
        if not node_profile:
            raise Exception("unknown node", node)
        
        if node_profile.node_type != NodeType.FULL:
            return
            # raise Exception("poll node", node)
        
        queue = self.webhook_event_queue.get(node)
        if not queue: return
        
        events = list()
        while not queue.empty():
            events.append(queue.get())
        
        self.adapter.broadcast_events(node, events=events)
        
        # TODO: retry if request failed
    
    def flush_all_webhook_queues(self):
        for node in self.webhook_event_queue.keys():
            self.flush_webhook_queue(node)
        