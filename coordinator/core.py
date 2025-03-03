from fastapi import FastAPI
from rid_lib.ext import Cache

from coordinator.network_adapter import Network


cache = Cache("coordinator_cache")
network = Network("sub_queue.json", cache)