import logging
from rich.logging import RichHandler
from koi_net.config.partial_node import PartialNodeConfig, KoiNetConfig, NodeProfile
from koi_net.core import PartialNode


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[RichHandler()]
)

logging.getLogger("koi_net").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


class MyPartialNodeConfig(PartialNodeConfig):
    koi_net: KoiNetConfig = KoiNetConfig(
        node_name="partial",
        node_profile=NodeProfile()
    )

class MyPartialNode(PartialNode):
    config_cls = MyPartialNodeConfig


if __name__ == "__main__":
    node = MyPartialNode()
    # node.entrypoint.run()