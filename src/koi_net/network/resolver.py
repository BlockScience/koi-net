import structlog
import httpx
from rid_lib import RID
from rid_lib.core import RIDType
from rid_lib.ext import Cache, Bundle
from rid_lib.types import KoiNetNode

from .graph import NetworkGraph
from .request_handler import RequestHandler
from ..protocol.node import NodeProfile, NodeType
from ..protocol.event import Event
from ..protocol.api_models import ErrorResponse
from ..identity import NodeIdentity
from ..config import NodeConfig

log = structlog.stdlib.get_logger()


class NetworkResolver:
    """Handles resolving nodes or knowledge objects from the network."""
    
    config: NodeConfig    
    identity: NodeIdentity
    cache: Cache
    graph: NetworkGraph
    request_handler: RequestHandler
    
    def __init__(
        self, 
        config: NodeConfig,
        cache: Cache, 
        identity: NodeIdentity,
        graph: NetworkGraph,
        request_handler: RequestHandler,
    ):
        self.config = config
        self.identity = identity
        self.cache = cache
        self.graph = graph
        self.request_handler = request_handler
        
        self.poll_event_queue = dict()
        self.webhook_event_queue = dict()
    
    def get_state_providers(self, rid_type: RIDType) -> list[KoiNetNode]:
        """Returns list of node RIDs which provide state for specified RID type."""
        
        log.debug(f"Looking for state providers of {rid_type}")
        provider_nodes = []
        for node_rid in self.cache.list_rids(rid_types=[KoiNetNode]):
            if node_rid == self.identity.rid:
                continue
            
            node_bundle = self.cache.read(node_rid)
            
            node_profile = node_bundle.validate_contents(NodeProfile)
            
            if (node_profile.node_type == NodeType.FULL) and (rid_type in node_profile.provides.state):
                log.debug(f"Found provider {node_rid!r}")
                provider_nodes.append(node_rid)
        
        if not provider_nodes:
            log.debug("Failed to find providers")
        return provider_nodes
            
    def fetch_remote_bundle(self, rid: RID) -> tuple[Bundle | None, KoiNetNode | None]:
        """Attempts to fetch a bundle by RID from known peer nodes."""
        
        log.debug(f"Fetching remote bundle {rid!r}")
        remote_bundle, node_rid = None, None
        for node_rid in self.get_state_providers(type(rid)):
            payload = self.request_handler.fetch_bundles(
                node=node_rid, rids=[rid])
            
            if payload.bundles:
                remote_bundle = payload.bundles[0]
                log.debug(f"Got bundle from {node_rid!r}")
                break
        
        if not remote_bundle:
            log.warning("Failed to fetch remote bundle")
            
        return remote_bundle, node_rid
    
    def fetch_remote_manifest(self, rid: RID) -> tuple[Bundle | None, KoiNetNode | None]:
        """Attempts to fetch a manifest by RID from known peer nodes."""
        
        log.debug(f"Fetching remote manifest {rid!r}")
        remote_manifest, node_rid = None, None
        for node_rid in self.get_state_providers(type(rid)):
            payload = self.request_handler.fetch_manifests(
                node=node_rid, rids=[rid])
            
            if payload.manifests:
                remote_manifest = payload.manifests[0]
                log.debug(f"Got bundle from {node_rid!r}")
                break
        
        if not remote_manifest:
            log.warning("Failed to fetch remote bundle")
            
        return remote_manifest, node_rid
    
    def poll_neighbors(self) -> dict[KoiNetNode, list[Event]]:
        """Polls all neighbor nodes and returns compiled list of events.
        
        Neighbor nodes also include the first contact, regardless of
        whether the first contact profile is known to this node.
        """
        
        graph_neighbors = self.graph.get_neighbors()
        neighbors = []
        
        if graph_neighbors:
            for node_rid in graph_neighbors:
                node_bundle = self.cache.read(node_rid)
                if not node_bundle: 
                    continue
                node_profile = node_bundle.validate_contents(NodeProfile)
                if node_profile.node_type != NodeType.FULL: 
                    continue
                neighbors.append(node_rid)
            
        elif self.config.koi_net.first_contact.rid:
            neighbors.append(self.config.koi_net.first_contact.rid)
        
        event_dict = dict()
        for node_rid in neighbors:
            try:
                payload = self.request_handler.poll_events(
                    node=node_rid, 
                    rid=self.identity.rid
                )
                
                if type(payload) == ErrorResponse:
                    continue
                    
                if payload.events:
                    log.debug(f"Received {len(payload.events)} events from {node_rid!r}")
                    
                    event_dict[node_rid] = payload.events
                    
            except httpx.ConnectError:
                log.debug(f"Failed to reach node {node_rid!r}")
                continue
        
        return event_dict