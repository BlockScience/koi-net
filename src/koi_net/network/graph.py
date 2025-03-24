import logging
from typing import Literal
import networkx as nx
from rid_lib import RID, RIDType
from rid_lib.ext.cache import Cache
from rid_lib.types import KoiNetEdge, KoiNetNode
from ..models import *

logger = logging.getLogger(__name__)


class NetworkGraph:
    def __init__(self, cache: Cache, me: RID):
        self.cache = cache
        self.dg = nx.DiGraph()
        self.me = me
        self.generate()
        
    def generate(self):
        logger.info("Generating network graph")
        self.dg.clear()
        for rid in self.cache.read_all_rids():
            if type(rid) == KoiNetNode:                
                self.dg.add_node(rid)
                logger.info(f"Added node {rid}")
                
            elif type(rid) == KoiNetEdge:
                edge_bundle = self.cache.read(rid)
                edge = EdgeModel(**edge_bundle.contents)
                self.dg.add_edge(edge.source, edge.target, rid=rid)
                logger.info(f"Added edge {edge.source} -> {edge.target}")
        logger.info("Done")
    
    def get_neighbors(
        self,
        direction: Literal["in", "out"] | None = None,
        status: Literal["proposed", "approved"] | None = None,
        allowed_type: RIDType | None = None
    ) -> list[RID]:
        
        neighbors = []
        for edge in self.dg.edges:
            edge_rid = self.dg.edges[edge]["rid"]
            
            if direction == "out" and edge[0] != self.me:
                continue
            if direction == "in" and edge[1] != self.me:
                continue
            
            edge_bundle = self.cache.read(edge_rid)
            if not edge_bundle: 
                logger.warning(f"Failed to find edge {edge_rid} in cache")
                continue
            
            edge = EdgeModel.model_validate(edge_bundle.contents)
            
            if status and edge.status != status:
                continue
            
            if allowed_type and allowed_type not in edge.rid_types:
                continue
            
            neighbors.append(edge.target)
                
        return neighbors
        
