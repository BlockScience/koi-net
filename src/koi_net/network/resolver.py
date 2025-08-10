import logging
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
from ..effector import Effector

logger = logging.getLogger(__name__)


class NetworkResolver:
    """A collection of functions and classes to interact with the KOI network."""
    
    config: NodeConfig    
    identity: NodeIdentity
    effector: Effector
    cache: Cache
    graph: NetworkGraph
    request_handler: RequestHandler
    
    def __init__(
        self, 
        config: NodeConfig,
        cache: Cache, 
        identity: NodeIdentity,
        effector: Effector,
        graph: NetworkGraph,
        request_handler: RequestHandler,
    ):
        self.config = config
        self.identity = identity
        self.cache = cache
        self.graph = graph
        self.request_handler = request_handler
        self.effector = effector
        
        self.poll_event_queue = dict()
        self.webhook_event_queue = dict()
    
    def get_state_providers(self, rid_type: RIDType) -> list[KoiNetNode]:
        """Returns list of node RIDs which provide state for the specified RID type."""
        
        logger.debug(f"Looking for state providers of '{rid_type}'")
        provider_nodes = []
        for node_rid in self.cache.list_rids(rid_types=[KoiNetNode]):
            if node_rid == self.identity.rid:
                continue
            
            node_bundle = self.cache.read(node_rid)
            
            node_profile = node_bundle.validate_contents(NodeProfile)
            
            if (node_profile.node_type == NodeType.FULL) and (rid_type in node_profile.provides.state):
                logger.debug(f"Found provider {node_rid!r}")
                provider_nodes.append(node_rid)
        
        if not provider_nodes:
            logger.debug("Failed to find providers")
        return provider_nodes
            
    def fetch_remote_bundle(self, rid: RID) -> tuple[Bundle | None, KoiNetNode | None]:
        """Attempts to fetch a bundle by RID from known peer nodes."""
        
        logger.debug(f"Fetching remote bundle {rid!r}")
        remote_bundle, node_rid = None, None
        for node_rid in self.get_state_providers(type(rid)):
            payload = self.request_handler.fetch_bundles(
                node=node_rid, rids=[rid])
            
            if payload.bundles:
                remote_bundle = payload.bundles[0]
                logger.debug(f"Got bundle from {node_rid!r}")
                break
        
        if not remote_bundle:
            logger.warning("Failed to fetch remote bundle")
            
        return remote_bundle, node_rid
    
    def fetch_remote_manifest(self, rid: RID) -> tuple[Bundle | None, KoiNetNode | None]:
        """Attempts to fetch a manifest by RID from known peer nodes."""
        
        logger.debug(f"Fetching remote manifest {rid!r}")
        remote_manifest, node_rid = None, None
        for node_rid in self.get_state_providers(type(rid)):
            payload = self.request_handler.fetch_manifests(
                node=node_rid, rids=[rid])
            
            if payload.manifests:
                remote_manifest = payload.manifests[0]
                logger.debug(f"Got bundle from {node_rid!r}")
                break
        
        if not remote_manifest:
            logger.warning("Failed to fetch remote bundle")
            
        return remote_manifest, node_rid
    
    def poll_neighbors(self) -> dict[KoiNetNode, list[Event]]:
        """Polls all neighboring nodes and returns compiled list of events.
        
        If this node has no neighbors, it will instead attempt to poll the provided first contact URL.
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
                    logger.debug(f"Received {len(payload.events)} events from {node_rid!r}")
                    
                    event_dict[node_rid] = payload.events
                    
            except httpx.ConnectError:
                logger.debug(f"Failed to reach node {node_rid!r}")
                continue
        
        return event_dict