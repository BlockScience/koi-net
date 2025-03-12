import httpx
from rid_lib import RID
from .models import *
from .state import NetworkState

class NetworkAdapter:
    def __init__(self, state: NetworkState):
        self.state = state
        
    # def make_request(self):
    #     try:
    #         httpx.post(
    #             url=...,
    #             data=...
    #         )
    
    def broadcast_events(self, node: RID = None, url: str = None, events=[]):
        base_url = self.state.get_node(node).base_url if node else url
                
        resp = httpx.post(
            url=base_url + KoiNetPath.EVENTS_BROADCAST,
            data=RetrieveEventsResp(events=events).model_dump_json()
        )
        print(resp.json())
        
    def poll_events(self, node: RID = None, url: str = None, **kwargs):
        base_url = self.state.get_node(node).base_url if node else url
        
        resp = httpx.post(
            url=base_url + KoiNetPath.EVENTS_POLL,
            data=PollEventsReq(**kwargs).model_dump_json()
        )
        
        return RetrieveEventsResp.model_validate(resp.json())
    
    def retrieve_rids(self, node: RID, **kwargs):
        node_profile = self.state.get_node(node)
        
        resp = httpx.post(
            url=node_profile.base_url + KoiNetPath.STATE_RIDS,
            data=RetrieveRidsReq(**kwargs).model_dump_json()
        )
        
        return RetrieveRidsResp.model_validate(resp.json())
        
        
    def retrieve_manifests(self, node: RID, **kwargs):
        node_profile = self.state.get_node(node)
        
        resp = httpx.post(
            url=node_profile.base_url + KoiNetPath.STATE_MANIFESTS,
            data=RetrieveManifestsReq(**kwargs).model_dump_json()
        )
        
        return RetrieveManifestsResp.model_validate(resp.json())
        
    def retrieve_bundles(self, node: RID, **kwargs):
        node_profile = self.state.get_node(node)
        
        resp = httpx.post(
            url=node_profile.base_url + KoiNetPath.STATE_BUNDLES,
            data=RetrieveBundlesReq(**kwargs).model_dump_json()
        )
        
        return RetrieveBundlesResp.model_validate(resp.json())
        
