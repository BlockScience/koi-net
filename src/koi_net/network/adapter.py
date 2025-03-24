import logging
import httpx
from pydantic import BaseModel
from rid_lib import RID
from rid_lib.ext import Cache
from ..models import (
    ApiPath,
    NodeType,
    NodeModel,
    RidsPayload,
    ManifestsPayload,
    BundlesPayload,
    EventsPayload,
    FetchRids,
    FetchManifests,
    FetchBundles,
    PollEvents
)

logger = logging.getLogger(__name__)


class NetworkAdapter:
    def __init__(self, cache: Cache):
        self.cache = cache
        
    def make_request(self, url, request: BaseModel):
        logger.info(f"Making request to {url}")
        resp = httpx.post(
            url=url,
            data=request.model_dump_json()
        )
        return resp
            
    def get_url(self, node_rid, url):
        if not node_rid and not url:
            raise ValueError("One of 'node_rid' and 'url' must be provided")
        
        if node_rid:
            bundle = self.cache.read(node_rid)
            node = NodeModel.model_validate(bundle.contents)
            if node.node_type != NodeType.FULL:
                raise Exception("Can't query partial node")
            logger.info(f"Resolved {node_rid!r} to {node.base_url}")
            return node.base_url
        else:
            return url
    
    def broadcast_events(self, node: RID = None, url: str = None, events=[]):
        self.make_request(
            self.get_url(node, url) + ApiPath.BROADCAST_EVENTS,
            EventsPayload(events=events)
        )
        
    def poll_events(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + ApiPath.POLL_EVENTS,
            PollEvents.model_validate(kwargs)
        )
        
        return EventsPayload.model_validate_json(resp.text)
    
    def fetch_rids(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + ApiPath.FETCH_RIDS,
            FetchRids.model_validate(kwargs)
        )
        
        return RidsPayload.model_validate_json(resp.text)
        
        
    def fetch_manifests(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + ApiPath.FETCH_MANIFESTS,
            FetchManifests.model_validate(kwargs)
        )
        
        return ManifestsPayload.model_validate_json(resp.text)
        
    def fetch_bundles(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + ApiPath.FETCH_BUNDLES,
            FetchBundles.model_validate(kwargs)
        )
        
        return BundlesPayload.model_validate_json(resp.text)
        
