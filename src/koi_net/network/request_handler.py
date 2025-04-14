import logging
import httpx
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
        logger.debug(f"Making request to {url}")
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
            logger.debug(f"Resolved {node_rid!r} to {node_profile.base_url}")
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
        request = req or EventsPayload.model_validate(kwargs)
        self.make_request(
            self.get_url(node, url) + BROADCAST_EVENTS_PATH, request
        )
        logger.info(f"Broadcasted {len(request.events)} event(s) to {node or url!r}")
        
    def poll_events(
        self, 
        node: RID = None, 
        url: str = None, 
        req: PollEvents | None = None,
        **kwargs
    ) -> EventsPayload:
        """See protocol.api_models.PollEvents for available kwargs."""
        request = req or PollEvents.model_validate(kwargs)
        resp = self.make_request(
            self.get_url(node, url) + POLL_EVENTS_PATH, request,
            response_model=EventsPayload
        )
        logger.info(f"Polled {len(resp.events)} events from {node or url!r}")
        return resp
        
    def fetch_rids(
        self, 
        node: RID = None, 
        url: str = None, 
        req: FetchRids | None = None,
        **kwargs
    ) -> RidsPayload:
        """See protocol.api_models.FetchRids for available kwargs."""
        request = req or FetchRids.model_validate(kwargs)
        resp = self.make_request(
            self.get_url(node, url) + FETCH_RIDS_PATH, request,
            response_model=RidsPayload
        )
        logger.info(f"Fetched {len(resp.rids)} RID(s) from {node or url!r}")
        return resp
                
    def fetch_manifests(
        self, 
        node: RID = None, 
        url: str = None, 
        req: FetchManifests | None = None,
        **kwargs
    ) -> ManifestsPayload:
        """See protocol.api_models.FetchManifests for available kwargs."""
        request = req or FetchManifests.model_validate(kwargs)
        resp = self.make_request(
            self.get_url(node, url) + FETCH_MANIFESTS_PATH, request,
            response_model=ManifestsPayload
        )
        logger.info(f"Fetched {len(resp.manifests)} manifest(s) from {node or url!r}")
        return resp
                
    def fetch_bundles(
        self, 
        node: RID = None, 
        url: str = None, 
        req: FetchBundles | None = None,
        **kwargs
    ) -> BundlesPayload:
        """See protocol.api_models.FetchBundles for available kwargs."""
        request = req or FetchBundles.model_validate(kwargs)
        resp = self.make_request(
            self.get_url(node, url) + FETCH_BUNDLES_PATH, request,
            response_model=BundlesPayload
        )
        logger.info(f"Fetched {len(resp.bundles)} bundle(s) from {node or url!r}")
        return resp