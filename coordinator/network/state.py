import networkx as nx
from rid_lib import RID
from rid_lib.ext.cache import Cache
from koi_net import EdgeModel, NodeModel
from rid_types import KoiNetEdge, KoiNetNode
from ..config import this_node_rid
from .models import *

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