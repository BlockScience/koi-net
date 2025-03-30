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
from ..protocol.node import NodeProfile, NodeType


logger = logging.getLogger(__name__)


class RequestHandler:
    cache: Cache
    
    def __init__(self, cache: Cache):
        self.cache = cache
                
    def make_request(self, url, request: BaseModel) -> httpx.Response:
        logger.info(f"Making request to {url}")
        resp = httpx.post(
            url=url,
            data=request.model_dump_json()
        )
        return resp
            
    def get_url(self, node_rid: KoiNetNode, url: str) -> str:
        if not node_rid and not url:
            raise ValueError("One of 'node_rid' and 'url' must be provided")
        
        if node_rid:
            # can't access get_node rn
            bundle = self.cache.read(node_rid)
            node = NodeProfile.model_validate(bundle.contents)
            if node.node_type != NodeType.FULL:
                raise Exception("Can't query partial node")
            logger.info(f"Resolved {node_rid!r} to {node.base_url}")
            return node.base_url
        else:
            return url
    
    def broadcast_events(
        self, node: RID = None, url: str = None, **kwargs
    ) -> None:
        self.make_request(
            self.get_url(node, url) + BROADCAST_EVENTS_PATH,
            EventsPayload.model_validate(kwargs)
        )
        
    def poll_events(
        self, node: RID = None, url: str = None, **kwargs
    ) -> EventsPayload:      
        resp = self.make_request(
            self.get_url(node, url) + POLL_EVENTS_PATH,
            PollEvents.model_validate(kwargs)
        )
        
        return EventsPayload.model_validate_json(resp.text)
    
    def fetch_rids(
        self, node: RID = None, url: str = None, **kwargs
    ) -> RidsPayload:      
        resp = self.make_request(
            self.get_url(node, url) + FETCH_RIDS_PATH,
            FetchRids.model_validate(kwargs)
        )
        
        return RidsPayload.model_validate_json(resp.text)
        
    def fetch_manifests(
        self, node: RID = None, url: str = None, **kwargs
    ) -> ManifestsPayload:    
        resp = self.make_request(
            self.get_url(node, url) + FETCH_MANIFESTS_PATH,
            FetchManifests.model_validate(kwargs)
        )
        
        return ManifestsPayload.model_validate_json(resp.text)
        
    def fetch_bundles(
        self, node: RID = None, url: str = None, **kwargs
    ) -> BundlesPayload:        
        resp = self.make_request(
            self.get_url(node, url) + FETCH_BUNDLES_PATH,
            FetchBundles.model_validate(kwargs)
        )
        
        return BundlesPayload.model_validate_json(resp.text)