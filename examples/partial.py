import logging
from pydantic import Field
from rich.logging import RichHandler
from koi_net.core import NodeAssembler
from koi_net.protocol.node import NodeProfile, NodeType
from koi_net.config import NodeConfig, KoiNetConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


class PartialNodeConfig(NodeConfig):
    koi_net: KoiNetConfig = Field(default_factory = lambda:
        KoiNetConfig(
            node_name="partial",
            node_profile=NodeProfile(
                node_type=NodeType.PARTIAL
            )
        )
    )

class PartialNodeAssembler(NodeAssembler):
    config = PartialNodeConfig


if __name__ == "__main__":
    node = PartialNodeAssembler.create()
    node.poller.run()