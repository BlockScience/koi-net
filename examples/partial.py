from koi_net.config import PartialNodeConfig, KoiNetConfig, PartialNodeProfile
from koi_net.core import PartialNode


class MyPartialNodeConfig(PartialNodeConfig):
    koi_net: KoiNetConfig = KoiNetConfig(
        node_name="partial",
        node_profile=PartialNodeProfile()
    )

class MyPartialNode(PartialNode):
    config_schema = MyPartialNodeConfig

if __name__ == "__main__":
    MyPartialNode().run()