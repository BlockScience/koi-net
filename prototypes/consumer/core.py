from fastapi import FastAPI
from rid_lib.ext import Cache

from .event_handler import KnowledgeProcessor
from .network_interface import NetworkInterface


cache = Cache("consumer_cache")
network = NetworkInterface("consumer_event_queues.json", cache)
processor = KnowledgeProcessor(cache, network)