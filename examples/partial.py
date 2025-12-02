from koi_net.config.partial_node import PartialNodeConfig, KoiNetConfig, NodeProfile
from koi_net.core import PartialNode


class MyPartialNodeConfig(PartialNodeConfig):
    koi_net: KoiNetConfig = KoiNetConfig(
        node_name="partial",
        node_profile=NodeProfile()
    )

class MyPartialNode(PartialNode):
    config_schema = MyPartialNodeConfig

if __name__ == "__main__":
    node = MyPartialNode()
    node.run()