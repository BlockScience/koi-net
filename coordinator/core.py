from rid_lib.ext import Bundle, Cache
from koi_net import NodeInterface
from .config import this_node_profile, this_node_rid

node = NodeInterface(
    rid=this_node_rid,
    cache=Cache("_cache-coordinator-node")
)

from . import handlers

node.processor.handle_state(Bundle.generate(
    rid=this_node_rid,
    contents=this_node_profile.model_dump()
))

this_node_bundle = node.cache.read(this_node_rid)
