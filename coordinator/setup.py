from contextlib import asynccontextmanager
from fastapi import FastAPI
from rid_lib.ext.bundle import Bundle
from .core import network, processor
from .config import this_node_profile, this_node_rid


@asynccontextmanager
async def lifespan(server: FastAPI):
    node_bundle = Bundle.generate(this_node_rid, this_node_profile.model_dump())
    processor.handle_state(node_bundle)
            
    yield
    
    network.save_queues()
        