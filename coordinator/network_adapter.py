from ast import Sub
import httpx
import networkx as nx
from rid_lib.core import RID
from rid_lib.ext.cache import Cache
from rid_lib.ext.event import Event
from koi_net import Edge, EventArray, KoiNetPath, Node, NodeType, SubQueue
from rid_types import KoiNetEdge, KoiNetNode
from .config import this_node_rid


class Network:
    def __init__(self, queue_path: str, cache: Cache):
        self.cache = cache
        self.dg = nx.DiGraph()
        self.generate_from_cache()
        
        self.sub_queue_path = queue_path
        self.sub_queue = self.load_queue()
        
        for sub in self.get_sub_rids():
            self.sub_queue.
        
    def generate_from_cache(self):
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
                edge = Edge(**edge_bundle.contents)
                
                self.dg.add_edge(
                    str(edge.source),
                    str(edge.target),
                    **edge_bundle.contents
                )
    
    def load_queue(self):
        try:
            with open(self.sub_queue_path, "r") as f:
                self.sub_queue = SubQueue.model_validate_json(f.read())
        except FileNotFoundError:
            return SubQueue()
        
    def save_queue(self):
        with open(self.sub_queue_path, "w") as f:
            f.write(self.sub_queue.model_dump_json(indent=2))
        
    def get_sub_rids(self, context: str | None = None):
        subscribers = self.dg.successors(str(this_node_rid))
        if context is None: 
            return list(subscribers)
        else:
            return [
                sub for sub in subscribers
                if context in self.dg.edges[str(this_node_rid), sub]["contexts"]
            ]
            
    def push_event(self, event: Event):
        subs = self.get_sub_rids(event.rid.context)
        for sub in subs:
            node_profile = Node(**self.dg.nodes[sub])
            if node_profile.node_type == NodeType.FULL:
                print("push to webhook", sub)
                self.sub_queue.webhook.setdefault(sub, list()).append(event)
            else:
                self.sub_queue.poll.setdefault(sub, list()).append(event)
            
    
    def get_node_profile(self, node_rid: RID):
        node_bundle = self.cache.read(node_rid)
        if not node_bundle: return None
        return Node(**node_bundle.contents)
        
    
    # def broadcast_event(self, peer_rid, event):
    #     peer_profile = self.get_node_profile(peer_rid)
    #     if not peer_profile:
    #         return
        
    #     if peer_profile.node_type == NodeType.PARTIAL:
    #         # TODO: push into event queue
    #         ...
    #     elif peer_profile.node_type == NodeType.FULL:
    #         httpx.post(
    #             peer_profile.base_url + KoiNetPath.EVENTS_BROADCAST,
    #             data=EventArray([event]).model_dump_json()
    #         )
    #         # TODO: handle failed request
        
    #     self.sub_map[event.rid]