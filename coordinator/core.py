import logging
from rich.logging import RichHandler
from rid_lib.ext import Bundle, Cache
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net import NodeInterface
from koi_net.protocol import NodeModel, NodeType, NodeProvides
from .config import host, port


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)

node = NodeInterface(
    rid=KoiNetNode("coordinator", "uuid"),
    profile=NodeModel(
        base_url=f"http://{host}:{port}/koi-net",
        node_type=NodeType.FULL,
        provides=NodeProvides(
            event=[KoiNetNode, KoiNetEdge],
            state=[KoiNetNode, KoiNetEdge]
        )
    ),
    cache=Cache("_cache-coordinator-node")
)

from . import handlers