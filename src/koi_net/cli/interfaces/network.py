import time

from koi_net.config.proxy import ConfigProxy

from ..exceptions import LocalNodeNotFoundError
from ..models import NetworkConfigLoader, KoiNetworkConfig
from .node import NodeInterface


class NetworkInterface:
    def __init__(self):
        self.config: KoiNetworkConfig = ConfigProxy()
        self.config_loader = NetworkConfigLoader(
            config_schema=KoiNetworkConfig,
            config=self.config
        )
        
        self.nodes: dict[str, NodeInterface] = {}
        
        
    def load_node(self, name: str) -> NodeInterface:
        if name not in self.config.nodes:
            raise Exception()
        
        module = self.config.nodes[name]
        return NodeInterface(name, module)
    
    def sync(self, verbose: bool = False):
        for name, node in self.nodes.items():
            if node.exists():
                continue
            
            node.create()
            node.init()
            
    def start(self, delay: float = 0.0):
        for name, node in self.nodes.items():
            print(f"starting {name}...")
            node.start()
            # time.sleep(delay)
        print("done!")
            
    def stop(self):
        for name, node in self.nodes.items():
            print(f"stopping {name}...")
            node.stop()
        print("done!")
        
    def add_node(self, node: NodeInterface):
        self.config.nodes[node.name] = node.module
        self.config_loader.save_to_yaml()
        
    def remove_node(self, node: NodeInterface):
        if node.name in self.config.nodes:
            del self.config.nodes[node.name]
            self.config_loader.save_to_yaml()
        
        if self.config.first_contact == node.name:
            network.config.first_contact = None
            self.config_loader.save_to_yaml()
        
        
if __name__ == "__main__":
    network = NetworkInterface()