import logging
from typing import Literal
import networkx as nx
from rid_lib import RID, RIDType
from rid_lib.ext import Cache
from rid_lib.types import KoiNetEdge, KoiNetNode
from ..identity import NodeIdentity
from ..protocol.edge import EdgeProfile, EdgeStatus

logger = logging.getLogger(__name__)


class NetworkGraph:
    def __init__(self, cache: Cache, identity: NodeIdentity):
        self.cache = cache
        self.dg = nx.DiGraph()
        self.identity = identity
        
    def generate(self):
        logger.info("Generating network graph")
        self.dg.clear()
        for rid in self.cache.list_rids():
            if type(rid) == KoiNetNode:                
                self.dg.add_node(rid)
                logger.info(f"Added node {rid}")
                
            elif type(rid) == KoiNetEdge:
                edge_bundle = self.cache.read(rid)
                edge = EdgeProfile(**edge_bundle.contents)
                self.dg.add_edge(edge.source, edge.target, rid=rid)
                logger.info(f"Added edge {rid} ({edge.source} -> {edge.target})")
        logger.info("Done")
        
    def get_edges(
        self,
        direction: Literal["in", "out"] | None = None,
    ) -> list[KoiNetEdge]:
        
        edges = []
        if direction != "in":
            out_edges = self.dg.out_edges(self.identity.rid)
            edges.extend([e for e in out_edges])
                
        if direction != "out":
            in_edges = self.dg.in_edges(self.identity.rid)
            edges.extend([e for e in in_edges])
                    
        edge_rids = []
        for edge in edges:
            edge_data = self.dg.get_edge_data(*edge)
            if not edge_data: continue
            edge_rid = edge_data.get("rid")
            if not edge_rid: continue
            edge_rids.append(edge_rid)
       
        return edge_rids
    
    def get_neighbors(
        self,
        direction: Literal["in", "out"] | None = None,
        status: EdgeStatus | None = None,
        allowed_type: RIDType | None = None
    ) -> list[KoiNetNode]:
        
        neighbors = []
        for edge_rid in self.get_edges(direction):
            edge_bundle = self.cache.read(edge_rid)
            if not edge_bundle: 
                logger.warning(f"Failed to find edge {edge_rid} in cache")
                continue
            
            edge = EdgeProfile.model_validate(edge_bundle.contents)
            
            if status and edge.status != status:
                continue
            
            if allowed_type and allowed_type not in edge.rid_types:
                continue
            
            if edge.target == self.identity.rid:
                neighbors.append(edge.source)
            elif edge.source == self.identity.rid:
                neighbors.append(edge.target)
                
        return list(neighbors)
        
