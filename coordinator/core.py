import logging
from rich.logging import RichHandler
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net import NodeInterface
from koi_net.identity import NodeIdentity
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from .config import host, port


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)

node = NodeInterface(
    name="coordinator",
    profile=NodeProfile(
        base_url=f"http://{host}:{port}/koi-net",
        node_type=NodeType.FULL,
        provides=NodeProvides(
            event=[KoiNetNode, KoiNetEdge],
            state=[KoiNetNode, KoiNetEdge]
        )
    ),
    identity_file_path="coordinator_identity.json"
)

from . import handlers