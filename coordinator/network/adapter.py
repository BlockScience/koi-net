import httpx
from rid_lib import RID
from koi_net import  EventArrayModel, KoiNetPath, ManifestArrayModel, RIDArrayModel, BundleArrayModel
from ..network_models import *
from .state import NetworkState

class NetworkAdapter:
    def __init__(self, state: NetworkState):
        self.state = state
    
    def broadcast_events(self, node: RID, events):
        node_profile = self.state.get_node(node)
                
        httpx.post(
            url=node_profile.base_url + KoiNetPath.EVENTS_BROADCAST,
            data=EventArrayModel(events).model_dump_json()
        )
    
    def retrieve_rids(self, node: RID, **kwargs):
        node_profile = self.state.get_node(node)
        
        resp = httpx.post(
            url=node_profile.base_url + KoiNetPath.STATE_RIDS,
            data=RetrieveRids(**kwargs).model_dump_json()
        )
        
        return RIDArrayModel.model_validate(resp.json()).root
        
        
    def retrieve_manifests(self, node: RID, **kwargs):
        node_profile = self.state.get_node(node)
        
        resp = httpx.post(
            url=node_profile.base_url + KoiNetPath.STATE_MANIFESTS,
            data=RetrieveManifests(**kwargs).model_dump_json()
        )
        
        return ManifestArrayModel.model_validate(resp.json()).root
        
    def retrieve_bundles(self, node: RID, **kwargs):
        node_profile = self.state.get_node(node)
        
        resp = httpx.post(
            url=node_profile.base_url + KoiNetPath.STATE_BUNDLES,
            data=RetrieveBundles(**kwargs).model_dump_json()
        )
        
        return BundleArrayModel.model_validate(resp.json()).root
        
