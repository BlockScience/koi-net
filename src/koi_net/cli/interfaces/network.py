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
        
    def load_node(self, name: str) -> NodeInterface:
        if name not in self.config.nodes:
            raise ValueError(f"Node '{name}' not found in config")
        
        module = self.config.nodes[name]
        return NodeInterface(name, module)
    
    def load_nodes(self) -> list[NodeInterface]:
        return [NodeInterface(n, m) for n, m in self.config.nodes.items()]
    
    def sync(self, verbose: bool = False):
        for name in self.config.nodes:
            node = self.load_node(name)
            if node.exists():
                continue
            
            node.create()
            node.init()
    
    def run(self):
        try:
            nodes = self.load_nodes()
        
            running_nodes: list[NodeInterface] = []
            for node in nodes:
                if not node.start():
                    break
                
                running_nodes.append(node)
            
            if len(nodes) != len(running_nodes):
                print("Aborting run")
                return
            
            print(f"Completed startup of {len(nodes)} nodes!")
            print("Press Ctrl + C to quit")
            while any(n.process.poll() is None for n in running_nodes):
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            for node in reversed(running_nodes):
                node.stop()
        
    def add_node(self, node: NodeInterface):
        self.config.nodes[node.name] = node.module
        self.config_loader.save_to_yaml()
        
    def remove_node(self, node: NodeInterface):
        if node.name in self.config.nodes:
            del self.config.nodes[node.name]
            self.config_loader.save_to_yaml()
        
        if self.config.first_contact == node.name:
            self.config.first_contact = None
            self.config_loader.save_to_yaml()
