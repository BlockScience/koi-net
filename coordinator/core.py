from rid_lib.ext import Cache, Bundle
from .event_handler import KnowledgeProcessor
from .network import NetworkInterface
from .config import this_node_profile, this_node_rid


cache = Cache("coordinator_cache")
network = NetworkInterface("coordinator_event_queues.json", cache)
processor = KnowledgeProcessor(cache, network)

processor.handle_state(Bundle.generate(
    rid=this_node_rid,
    contents=this_node_profile.model_dump()
))

this_node_bundle = cache.read(this_node_rid)