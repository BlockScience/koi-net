from pydantic import BaseModel, RootModel
from rid_lib.ext import EventType, utils, Bundle, Cache, Event
from rid_lib.ext.pydantic_adapter import RIDField

class Provides(BaseModel):
    event: list[str] = []
    state: list[str] = []

class Node(BaseModel):
    base_url: str
    provides: Provides
    
class Edge(BaseModel):
    source: RIDField
    target: RIDField
    comm_type: str
    contexts: list[str]
    status: str
    
EventArray = RootModel[list[Event]]
    
def cache_compare(cache: Cache, curr_bundle: Bundle):
    prev_bundle = cache.read(curr_bundle.manifest.rid)
    if prev_bundle is None: 
        return EventType.NEW
    
    hashed_contents = utils.sha256_hash_json(curr_bundle.contents) 
    if (prev_bundle.manifest.sha256_hash != hashed_contents): 
        return EventType.UPDATE