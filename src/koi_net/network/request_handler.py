import logging
import httpx
from pydantic import BaseModel
from rid_lib import RID
from rid_lib.ext import Cache
from rid_lib.types.koi_net_node import KoiNetNode
from ..protocol.api_models import (
    RidsPayload,
    ManifestsPayload,
    BundlesPayload,
    EventsPayload,
    FetchRids,
    FetchManifests,
    FetchBundles,
    PollEvents
)
from ..protocol.consts import (
    BROADCAST_EVENTS_PATH,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH
)
from ..protocol.node import NodeType
from .graph import NetworkGraph


logger = logging.getLogger(__name__)


class RequestHandler:
    """Handles making requests to other KOI nodes."""
    
    cache: Cache
    graph: NetworkGraph
    
    def __init__(self, cache: Cache, graph: NetworkGraph):
        self.cache = cache
        self.graph = graph
                
    def make_request(self, url, request: BaseModel) -> httpx.Response:
        logger.info(f"Making request to {url}")
        resp = httpx.post(
            url=url,
            data=request.model_dump_json()
        )
        return resp
            
    def get_url(self, node_rid: KoiNetNode, url: str) -> str:
        """Retrieves URL of a node, or returns provided URL."""
        
        if not node_rid and not url:
            raise ValueError("One of 'node_rid' and 'url' must be provided")
        
        if node_rid:
            node_profile = self.graph.get_node_profile(node_rid)
            if not node_profile:
                raise Exception("Node not found")
            if node_profile.node_type != NodeType.FULL:
                raise Exception("Can't query partial node")
            logger.info(f"Resolved {node_rid!r} to {node_profile.base_url}")
            return node_profile.base_url
        else:
            return url
    
    def broadcast_events(
        self, node: RID = None, url: str = None, **kwargs
    ) -> None:
        """See protocol.api_models.EventsPayload for available kwargs."""
        self.make_request(
            self.get_url(node, url) + BROADCAST_EVENTS_PATH,
            EventsPayload.model_validate(kwargs)
        )
        
    def poll_events(
        self, node: RID = None, url: str = None, **kwargs
    ) -> EventsPayload:
        """See protocol.api_models.PollEvents for available kwargs."""
        resp = self.make_request(
            self.get_url(node, url) + POLL_EVENTS_PATH,
            PollEvents.model_validate(kwargs)
        )
        
        return EventsPayload.model_validate_json(resp.text)
    
    def fetch_rids(
        self, node: RID = None, url: str = None, **kwargs
    ) -> RidsPayload:
        """See protocol.api_models.FetchRids for available kwargs."""
        resp = self.make_request(
            self.get_url(node, url) + FETCH_RIDS_PATH,
            FetchRids.model_validate(kwargs)
        )
        
        return RidsPayload.model_validate_json(resp.text)
        
    def fetch_manifests(
        self, node: RID = None, url: str = None, **kwargs
    ) -> ManifestsPayload:
        """See protocol.api_models.FetchManifests for available kwargs."""
        resp = self.make_request(
            self.get_url(node, url) + FETCH_MANIFESTS_PATH,
            FetchManifests.model_validate(kwargs)
        )
        
        return ManifestsPayload.model_validate_json(resp.text)
        
    def fetch_bundles(
        self, node: RID = None, url: str = None, **kwargs
    ) -> BundlesPayload:
        """See protocol.api_models.FetchBundles for available kwargs."""
        resp = self.make_request(
            self.get_url(node, url) + FETCH_BUNDLES_PATH,
            FetchBundles.model_validate(kwargs)
        )
        
        return BundlesPayload.model_validate_json(resp.text)