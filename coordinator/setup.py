from contextlib import asynccontextmanager
from fastapi import FastAPI
from rid_lib.ext.bundle import Bundle
from koi_net import cache_compare
from .core import cache, network_state
from .config import this_node_profile, this_node_rid


@asynccontextmanager
async def lifespan(server: FastAPI):
    node_bundle = Bundle.generate(this_node_rid, this_node_profile.model_dump())
    cache_state = cache_compare(cache, node_bundle)
    
    print(cache_state)
    
    if cache_state is not None:
        cache.write(node_bundle)
        
    print(node_bundle)
    
    network_state.load_queue()
        
    yield
    
    network_state.save_queue()
        