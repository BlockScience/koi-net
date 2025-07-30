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


class PartialNodeConfig(NodeConfig):
    koi_net: KoiNetConfig | None = Field(default_factory = lambda:
        KoiNetConfig(
            node_name="partial",
            node_profile=NodeProfile(
                node_type=NodeType.PARTIAL
            ),
            cache_directory_path=".basic_partial_rid_cache",
            event_queues_path="basic_partial_event_queues.json",
            first_contact_rid="orn:koi-net.node:coordinator+0579755bf9371c0380e50ecc223bf1ab73f8a437034b1c685cb85fa0460b8a85",
            first_contact_url="http://127.0.0.1:8000/koi-net"
        )
    )


node = NodeInterface(
    config=PartialNodeConfig.load_from_yaml("basic_partial_config.yaml")
)


node.start()

while True:
    for event in node.resolver.poll_neighbors():
        node.processor.handle(event=event, source=KnowledgeSource.External)
    node.processor.flush_kobj_queue()
    
    time.sleep(5)