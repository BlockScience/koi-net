from pydantic import BaseModel
from rid_lib import RIDType
from rid_lib.types import KoiNetNode

from ..protocol.node import NodeProfile


class EventWorkerConfig(BaseModel):
    queue_timeout: float = 0.1
    max_buf_len: int = 5
    max_wait_time: float = 1.0
    
class KobjWorkerConfig(BaseModel):
    queue_timeout: float = 0.1

class NodeContact(BaseModel):
    rid: KoiNetNode | None = None
    url: str | None = None

class KoiNetConfig(BaseModel):
    """Config for KOI-net parameters."""
    
    node_name: str
    node_rid: KoiNetNode | None = None
    node_profile: NodeProfile
    
    rid_types_of_interest: list[RIDType] = [KoiNetNode]
        
    cache_directory_path: str = ".rid_cache"
    private_key_pem_path: str = "priv_key.pem"
    
    event_worker: EventWorkerConfig = EventWorkerConfig()
    kobj_worker: KobjWorkerConfig = KobjWorkerConfig()
    
    first_contact: NodeContact = NodeContact()