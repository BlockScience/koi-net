import time
import logging
from pydantic import Field
from rich.logging import RichHandler
from koi_net import NodeInterface
from koi_net.processor.knowledge_object import KnowledgeSource
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


class CoordinatorNodeConfig(NodeConfig):
    koi_net: KoiNetConfig | None = Field(default_factory = lambda:
        KoiNetConfig(
            node_name="coordinator",
            node_profile=NodeProfile(
                node_type=NodeType.FULL
            ),
            cache_directory_path=".basic_partial_rid_cache",
            event_queues_path="basic_partial_event_queues.json",
            first_contact="http://127.0.0.1:8000/koi-net"
        )
    )


node = NodeInterface(
    config=CoordinatorNodeConfig.load_from_yaml("basical_partial_config.yaml")
)

node.start()

while True:
    for event in node.network.poll_neighbors():
        node.processor.handle(event=event, source=KnowledgeSource.External)
    node.processor.flush_kobj_queue()
    
    time.sleep(5)