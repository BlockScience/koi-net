import logging
from typing import Literal
import networkx as nx
from rid_lib import RIDType
from rid_lib.ext import Cache
from rid_lib.types import KoiNetEdge, KoiNetNode
from ..identity import NodeIdentity
from ..protocol.edge import EdgeProfile, EdgeStatus
from ..protocol.node import NodeProfile

logger = logging.getLogger(__name__)


class NetworkGraph:
    """Graph functions for this node's view of its network."""
    
    cache: Cache
    identity: NodeIdentity
    dg: nx.DiGraph
    
    def __init__(self, cache: Cache, identity: NodeIdentity):
        self.cache = cache
        self.dg = nx.DiGraph()
        self.identity = identity
        
    def generate(self):
        """Generates directed graph from cached KOI nodes and edges."""
        logger.debug("Generating network graph")
        self.dg.clear()
        for rid in self.cache.list_rids():
            if type(rid) == KoiNetNode:                
                self.dg.add_node(rid)
                logger.debug(f"Added node {rid}")
                
            elif type(rid) == KoiNetEdge:
                edge_profile = self.get_edge_profile(rid)
                if not edge_profile:
                    logger.warning(f"Failed to load {rid!r}")
                    continue
                self.dg.add_edge(edge_profile.source, edge_profile.target, rid=rid)
                logger.debug(f"Added edge {rid} ({edge_profile.source} -> {edge_profile.target})")
        logger.debug("Done")
        
    def get_node_profile(self, rid: KoiNetNode) -> NodeProfile | None:
        """Returns node profile given its RID."""
        bundle = self.cache.read(rid)
        if bundle:
            return bundle.validate_contents(NodeProfile)
        
    def get_edge_profile(
        self, 
        rid: KoiNetEdge | None = None,
        source: KoiNetNode | None = None, 
        target: KoiNetNode | None = None,
    ) -> EdgeProfile | None:
        """Returns edge profile given its RID, or source and target node RIDs."""
        if source and target:
            if (source, target) not in self.dg.edges: return
            edge_data = self.dg.get_edge_data(source, target)
            if not edge_data: return
            rid = edge_data.get("rid")
            if not rid: return
        elif not rid:
            raise ValueError("Either 'rid' or 'source' and 'target' must be provided")
        
        bundle = self.cache.read(rid)
        if bundle:
            return bundle.validate_contents(EdgeProfile)
        
    def get_edges(
        self,
        direction: Literal["in", "out"] | None = None,
    ) -> list[KoiNetEdge]:
        """Returns edges this node belongs to.
        
        All edges returned by default, specify `direction` to restrict to incoming or outgoing edges only."""
                
        edges = []
        if direction != "in" and self.dg.out_edges:
            out_edges = self.dg.out_edges(self.identity.rid)
            edges.extend([e for e in out_edges])
                
        if direction != "out" and self.dg.in_edges:
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
        """Returns neighboring nodes this node shares an edge with.
        
        All neighboring nodes returned by default, specify `direction` to restrict to neighbors connected by incoming or outgoing edges only."""
        
        neighbors = []
        for edge_rid in self.get_edges(direction):
            edge_profile = self.get_edge_profile(edge_rid)
            
            if not edge_profile: 
                logger.warning(f"Failed to find edge {edge_rid!r} in cache")
                continue
                        
            if status and edge_profile.status != status:
                continue
            
            if allowed_type and allowed_type not in edge_profile.rid_types:
                continue
            
            if edge_profile.target == self.identity.rid:
                neighbors.append(edge_profile.source)
            elif edge_profile.source == self.identity.rid:
                neighbors.append(edge_profile.target)
                
        return list(neighbors)
        
