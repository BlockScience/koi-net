from fastapi import FastAPI
from rid_lib.ext import Cache

from .event_handler import KnowledgeProcessor
from .network_interface import NetworkInterface


cache = Cache("coordinator_cache")
network = NetworkInterface("coordinator_event_queues.json", cache)
processor = KnowledgeProcessor(cache, network)