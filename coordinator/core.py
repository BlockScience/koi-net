from fastapi import FastAPI
from rid_lib.ext import Cache

from coordinator.event_handler import KnowledgeProcessor
from coordinator.network_state import NetworkState


cache = Cache("coordinator_cache")
network_state = NetworkState("sub_queue.json", cache)
processor = KnowledgeProcessor(cache, network_state)