
from pathlib import Path
import time

from pydantic import BaseModel

from koi_net.build.container import NodeState
from koi_net.interface.exceptions import LocalNodeNotFoundError

from ..config.proxy import ConfigProxy
from ..config.loader import ConfigLoader
from .node import NodeInterface


class KoiNetworkConfig(BaseModel):
    first_contact: str | None = None
    nodes: dict[str, str] = {}

class NetworkConfigLoader(ConfigLoader):
    file_path: str = "koi-network-config.yaml"

class NetworkInterface:
    def __init__(self):
        self.config: KoiNetworkConfig = ConfigProxy()
        self.config_loader = NetworkConfigLoader(
            config_schema=KoiNetworkConfig,
            config=self.config,
            root_dir=Path.cwd()
        )
        
        self.nodes: list[NodeInterface] = self.load_nodes()
    
    # def load_node(self, name: str) -> NodeInterface:
    #     if name not in self.config.nodes:
    #         raise ValueError(f"Node '{name}' not found in config")
        
    #     module_name = self.config.nodes[name]
    #     return NodeInterface(name, module_name)
    
    def load_nodes(self) -> list[NodeInterface]:
        nodes = [
            NodeInterface(name, module) for name, module in self.config.nodes.items()
        ]
        print(f"Loaded {len(nodes)} nodes")
        return nodes
        
    def resolve_node(self, name: str) -> NodeInterface:
        for node in self.nodes:
            if node.name == name:
                return node
        
        raise LocalNodeNotFoundError(f"Node '{name}' not found")
    
    def add_node(self, node: NodeInterface):
        self.nodes.append(node)
        self.config.nodes[node.name] = node.module
        self.config_loader.save_to_yaml()
        
    def remove_node(self, node: NodeInterface):
        self.nodes.remove(node)
        
        if node.name in self.config.nodes:
            del self.config.nodes[node.name]
            self.config_loader.save_to_yaml()
        
        # do this with sync!
        # if self.config.first_contact == node.name:
        #     self.config.first_contact = None
        #     self.config_loader.save_to_yaml()
    
    def sync(self):
        for node in self.nodes:
            if not node.exists():
                node.create()
                node.init()
        
        first_contact = self.config.first_contact
        if first_contact:
            if first_contact in self.config.nodes:
                # configure first contact for unconfigured nodes
                
                fc_node = self.resolve_node(first_contact)
                fc_rid = fc_node.container.config.koi_net.node_rid
                fc_url = fc_node.container.config.koi_net.node_profile.base_url
                
                for node in self.nodes:
                    if node is fc_node:
                        continue
                    
                    with node.mutate_config() as config:
                        config.koi_net.first_contact.rid = fc_rid
                        config.koi_net.first_contact.url = fc_url
                    
            else:
                # unset firstcontact for configured nodes -- wait how would i know?
                # dependent on prev state ie which node removed
                ...
                
    def state(self):
        for node in self.nodes:
            print(node.name, node.state())
    
    def run(self):
        try:
            self.start()
            
            print(f"Completed startup of {len(self.nodes)} nodes!")
            print("Press Ctrl + C to quit")
            while any(n.state() is NodeState.RUNNING for n in self.nodes):
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            pass
        
        finally:
            self.stop()
    
    def start(self):
        for node in self.nodes:
            if node.state() == NodeState.IDLE:
                node.start()
            
    def stop(self):
        for node in reversed(self.nodes):
            if node.state() == NodeState.RUNNING:
                node.stop()
        
