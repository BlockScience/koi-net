from fastapi import FastAPI
from rid_lib.ext import Cache

from coordinator.event_handler import KnowledgeProcessor
from coordinator.network_interface import NetworkInterface


cache = Cache("coordinator_cache")
network = NetworkInterface("event_queues.json", cache)
processor = KnowledgeProcessor(cache, network)