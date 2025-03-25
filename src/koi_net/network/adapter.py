import logging
import httpx
from pydantic import BaseModel
from rid_lib import RID
from rid_lib.ext import Cache
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
from ..protocol.node import NodeModel, NodeType


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
            self.get_url(node, url) + BROADCAST_EVENTS_PATH,
            EventsPayload(events=events)
        )
        
    def poll_events(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + POLL_EVENTS_PATH,
            PollEvents.model_validate(kwargs)
        )
        
        return EventsPayload.model_validate_json(resp.text)
    
    def fetch_rids(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + FETCH_RIDS_PATH,
            FetchRids.model_validate(kwargs)
        )
        
        return RidsPayload.model_validate_json(resp.text)
        
        
    def fetch_manifests(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + FETCH_MANIFESTS_PATH,
            FetchManifests.model_validate(kwargs)
        )
        
        return ManifestsPayload.model_validate_json(resp.text)
        
    def fetch_bundles(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + FETCH_BUNDLES_PATH,
            FetchBundles.model_validate(kwargs)
        )
        
        return BundlesPayload.model_validate_json(resp.text)
        
