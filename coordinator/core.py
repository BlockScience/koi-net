import logging
from rich.logging import RichHandler
from rid_lib.ext import Bundle, Cache
from koi_net import NodeInterface
from .config import this_node_profile, this_node_rid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)

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
