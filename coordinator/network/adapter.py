import httpx
from rid_lib import RID
from .models import *
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
            self.get_url(node, url) + KoiNetPath.EVENTS_BROADCAST,
            EventsPayload(events=events)
        )
        
    def poll_events(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + KoiNetPath.EVENTS_POLL,
            RequestEvents(**kwargs)
        )
        
        return EventsPayload.model_validate(resp)
    
    def retrieve_rids(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + KoiNetPath.STATE_RIDS,
            RequestRids(**kwargs)
        )
        
        return RidsPayload.model_validate(resp)
        
        
    def retrieve_manifests(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + KoiNetPath.STATE_MANIFESTS,
            RequestManifests(**kwargs)
        )
        
        return ManifestsPayload.model_validate(resp)
        
    def retrieve_bundles(self, node: RID = None, url: str = None, **kwargs):        
        resp = self.make_request(
            self.get_url(node, url) + KoiNetPath.STATE_BUNDLES,
            RequestBundles(**kwargs)
        )
        
        return BundlesPayload.model_validate(resp)
        
