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
            node_name="partial",
            node_profile=NodeProfile(
                node_type=NodeType.PARTIAL
            ),
            cache_directory_path=".basic_partial_rid_cache",
            event_queues_path="basic_partial_event_queues.json",
            first_contact="orn:koi-net.node:coordinator+0579755bf9371c0380e50ecc223bf1ab73f8a437034b1c685cb85fa0460b8a85"
        )
    )


node = NodeInterface(
    config=CoordinatorNodeConfig.load_from_yaml("basic_partial_config.yaml")
)

print(node.config.koi_net.first_contact)

node.start()

while True:
    for event in node.network.poll_neighbors():
        node.processor.handle(event=event, source=KnowledgeSource.External)
    node.processor.flush_kobj_queue()
    
    time.sleep(5)