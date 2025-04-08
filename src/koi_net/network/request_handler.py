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
    PollEvents,
    RequestModels,
    ResponseModels
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
                
    def make_request(
        self, 
        url: str, 
        request: RequestModels,
        response_model: type[ResponseModels] | None = None
    ) -> ResponseModels | None:
        logger.info(f"Making request to {url}")
        resp = httpx.post(
            url=url,
            data=request.model_dump_json()
        )
        if response_model:
            return response_model.model_validate_json(resp.text)
            
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
        self, 
        node: RID = None, 
        url: str = None, 
        req: EventsPayload | None = None,
        **kwargs
    ) -> None:
        """See protocol.api_models.EventsPayload for available kwargs."""
        self.make_request(
            self.get_url(node, url) + BROADCAST_EVENTS_PATH,
            req or EventsPayload.model_validate(kwargs)
        )
        
    def poll_events(
        self, 
        node: RID = None, 
        url: str = None, 
        req: PollEvents | None = None,
        **kwargs
    ) -> EventsPayload:
        """See protocol.api_models.PollEvents for available kwargs."""
        return self.make_request(
            self.get_url(node, url) + POLL_EVENTS_PATH,
            req or PollEvents.model_validate(kwargs),
            response_model=EventsPayload
        )
            
    def fetch_rids(
        self, 
        node: RID = None, 
        url: str = None, 
        req: FetchRids | None = None,
        **kwargs
    ) -> RidsPayload:
        """See protocol.api_models.FetchRids for available kwargs."""
        return self.make_request(
            self.get_url(node, url) + FETCH_RIDS_PATH,
            req or FetchRids.model_validate(kwargs),
            response_model=RidsPayload
        )
                
    def fetch_manifests(
        self, 
        node: RID = None, 
        url: str = None, 
        req: FetchManifests | None = None,
        **kwargs
    ) -> ManifestsPayload:
        """See protocol.api_models.FetchManifests for available kwargs."""
        return self.make_request(
            self.get_url(node, url) + FETCH_MANIFESTS_PATH,
            req or FetchManifests.model_validate(kwargs),
            response_model=ManifestsPayload
        )
                
    def fetch_bundles(
        self, 
        node: RID = None, 
        url: str = None, 
        req: FetchBundles | None = None,
        **kwargs
    ) -> BundlesPayload:
        """See protocol.api_models.FetchBundles for available kwargs."""
        return self.make_request(
            self.get_url(node, url) + FETCH_BUNDLES_PATH,
            req or FetchBundles.model_validate(kwargs),
            response_model=BundlesPayload
        )