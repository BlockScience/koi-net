import networkx as nx
from rid_lib import RID
from rid_lib.ext.cache import Cache
from ..rid_types import KoiNetEdge, KoiNetNode
from ..models import *

class NetworkState:
    def __init__(self, cache: Cache, me: RID):
        self.cache = cache
        self.dg = nx.DiGraph()
        self.me = me
        self.generate()
        
    def generate(self):
        print("generating network state...")
        self.dg.clear()
        for rid in self.cache.read_all_rids():
            if rid.context == KoiNetNode.context:
                node_bundle = self.cache.read(rid)
                
                print("\t> adding node", rid)
                self.dg.add_node(
                    str(rid),
                    **node_bundle.contents
                )
                
            elif rid.context == KoiNetEdge.context:
                edge_bundle = self.cache.read(rid)
                edge = EdgeModel(**edge_bundle.contents)
                
                print("\t> adding edge", edge.source, "->", edge.target)
                self.dg.add_edge(
                    str(edge.source),
                    str(edge.target),
                    **edge_bundle.contents
                )
        print("\tdone.\n")
        
    def get_adjacent_rids(self, nodes, forward=True, context: str | None = None):
        subscribers = []
        for sub_rid in nodes:
            edge_profile = EdgeModel.model_validate(
                self.dg.edges[str(self.me), sub_rid] if forward else self.dg.edges[sub_rid, str(self.me)])
            if edge_profile.status != "approved": continue
            if context and (context not in edge_profile.contexts): continue
            subscribers.append(RID.from_string(sub_rid))
        return subscribers
    
    
    def get_sub_rids(self, context: str | None = None):
        return self.get_adjacent_rids(self.dg.successors(str(self.me)), False, context)
    
    def get_pub_rids(self, context: str | None = None):
        return self.get_adjacent_rids(self.dg.predecessors(str(self.me)), True, context)
            
    def get_node(self, node: RID):
        node_contents = self.dg.nodes.get(str(node))
        if node_contents:
            return NodeModel(**node_contents)