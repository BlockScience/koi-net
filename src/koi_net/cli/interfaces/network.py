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
        
        self.load_nodes()
    
    def load_nodes(self):
        for name, module in self.config.nodes.items():
            self.nodes[name] = NodeInterface(name, module)
            
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
        
    def add_node(self, name: str, module: str, no_local: bool = False):
        node = NodeInterface(name, module)
        if not no_local:
            node.create()
        
        self.nodes[name] = node
        self.config.nodes[name] = module
        self.config_loader.save_to_yaml()
        
    def remove_node(self, name: str):
        if name not in self.nodes:
            raise LocalNodeNotFoundError(f"Node '{name}' not found")
        
        self.nodes[name].delete()
        del self.nodes[name]
        del self.config.nodes[name]
        self.config_loader.save_to_yaml()
        
        
if __name__ == "__main__":
    network = NetworkInterface()