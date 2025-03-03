import httpx
from rid_lib.ext import Event
from koi_net import EventArray, KoiNetPath, Node
from rid_types import KoiNetNode
from .network_state import NetworkState

class NetworkAdapter:
    def __init__(self, net_state: NetworkState):
        self.net_state = net_state
        
    
    def broadcast_to_node(self, node: KoiNetNode):
        node_profile = Node(**self.net_state.get_node(node))
        
        if node_profile.node_type != "FULL": raise Exception("can't broadcast to partial nodes")
        
        events = self.net_state.sub_queue.poll.get(node)
        if not events: return
        self.net_state.sub_queue.poll.clear()
        
        httpx.post(
            url=node_profile.base_url + KoiNetPath.EVENTS_BROADCAST,
            data=EventArray(events).model_dump_json()
        )
