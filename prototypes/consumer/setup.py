from contextlib import asynccontextmanager
from fastapi import FastAPI
from rid_lib.ext import Bundle, Event, EventType
from koi_net import EdgeModel
from koi_net.rid_types import KoiNetEdge
from .core import network, processor
from .config import this_node_profile, this_node_rid


@asynccontextmanager
async def lifespan(server: FastAPI):
    node_bundle = Bundle.generate(this_node_rid, this_node_profile.model_dump())
    processor.handle_state(node_bundle)
    
    peer_bundle = network.adapter.handshake("http://127.0.0.1:8000/koi-net", node_bundle)
    processor.handle_state(peer_bundle)
    
    edge_bundle = Bundle.generate(
        KoiNetEdge("full_edge_test"),    
        EdgeModel(
            source=peer_bundle.manifest.rid,
            target=this_node_rid,
            comm_type="poll",
            contexts=[
                "orn:koi-net.node",
                "orn:koi-net.edge"
            ],
            status="proposed"
        ).model_dump()
    )
    
    network.adapter.broadcast_events(
        node=peer_bundle.manifest.rid,
        events=[Event(
            rid=edge_bundle.manifest.rid,
            event_type=EventType.NEW,
            bundle=edge_bundle
        )]
    )
        
    yield
    
    network.save_queues()
        