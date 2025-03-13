import httpx
from rid_lib import RID
from ..models import *
from .state import NetworkState

class NetworkAdapter:
    def __init__(self, state: NetworkState):
        self.state = state
        
    def make_request(self, url, model: BaseModel):
        try:
            resp = httpx.post(
                url=url,
                data=model.model_dump_json()
            )
            return resp.json()
        except httpx.RequestError as err:
            print(err)
            
    def get_url(self, node, url):
        if node:
            bundle = self.state.get_node(node)
            if not bundle:
                raise Exception
            return bundle.base_url
        else:
            return url
    
    def broadcast_events(self, node: RID = None, url: str = None, events=[]):
        resp = self.make_request(
            self.get_url(node, url) + ApiPath.BROADCAST_EVENTS,
            EventsPayload(events=events)
        )
        
    def poll_events(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + ApiPath.POLL_EVENTS,
            PollEvents(**kwargs)
        )
        
        return EventsPayload.model_validate(resp)
    
    def retrieve_rids(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + ApiPath.FETCH_RIDS,
            FetchRids(**kwargs)
        )
        
        return RidsPayload.model_validate(resp)
        
        
    def retrieve_manifests(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + ApiPath.FETCH_MANIFESTS,
            FetchManifests(**kwargs)
        )
        
        return ManifestsPayload.model_validate(resp)
        
    def retrieve_bundles(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + ApiPath.FETCH_BUNDLES,
            FetchBundles(**kwargs)
        )
        
        return BundlesPayload.model_validate(resp)
        
