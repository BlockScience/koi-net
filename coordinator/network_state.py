import networkx as nx
from rid_lib import RID
from rid_lib.ext.cache import Cache
from rid_lib.ext.event import Event
from koi_net import Edge, Node, NodeType, SubQueue
from rid_types import KoiNetEdge, KoiNetNode
from .config import this_node_rid


class NetworkState:
    def __init__(self, queue_path: str, cache: Cache):
        self.cache = cache
        self.dg = nx.DiGraph()
        self.generate_from_cache()
        
        self.sub_queue_path = queue_path
        self.sub_queue = self.load_queue()
        
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
            
    def get_node(self, node: RID):
        return Node(**self.dg.nodes.get(str(node)))
            
    def push_event(self, event: Event):
        subs = self.get_sub_rids(event.rid.context)
        for sub in subs:
            self.push_event_to(event, sub)
                
    def push_event_to(self, event: Event, node: KoiNetEdge):
        print("pushing event", event.event_type, event.rid, "to", node)
        node_profile = self.get_node(node)
        if node_profile.node_type == NodeType.FULL:
            self.sub_queue.webhook.setdefault(node, list()).append(event)
        else:
            self.sub_queue.poll.setdefault(node, list()).append(event)
        
        print(self.sub_queue)