
import time
from pathlib import Path

from pydantic import BaseModel
from rich.console import Console

from koi_net.config.base import BaseNodeConfig
from koi_net.protocol.node import NodeType

from ..build.container import NodeState
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
        self.config: ConfigProxy | KoiNetworkConfig = ConfigProxy()
        self.config_schema = KoiNetworkConfig
        self.config_loader = NetworkConfigLoader(
            config_schema=self.config_schema,
            config=self.config,
            root_dir=Path.cwd()
        )
        
        self.console = Console()
        
        self.nodes: list[NodeInterface] = []
        self.load_nodes()
    
    def load_nodes(self) -> list[NodeInterface]:
        for name, module in self.config.nodes.items():
            node = NodeInterface.from_ref(name, module)
            self.nodes.append(node)
            
            if node.exists():
                # print(f"Loading node '{node.name}'...")
                node.init()
            
    def resolve_node(self, name: str) -> NodeInterface | None:
        for node in self.nodes:
            if node.name == name:
                return node
            
    def add_node(self, node: NodeInterface):
        self.nodes.append(node)
        self.config.nodes[node.name] = node.module
        self.config_loader.save_to_yaml()
        
        fc_node = self.get_first_contact()
        if fc_node:
            with node.mutate_config() as config:
                self.apply_first_contact(
                    source=fc_node.node.config,
                    target=config
                )
    
    def remove_node(self, node: NodeInterface):
        self.nodes.remove(node)
        
        if node.name in self.config.nodes:
            del self.config.nodes[node.name]
            self.config_loader.save_to_yaml()
            
        if self.config.first_contact == node.name:
            self.unset_first_contact(node)
    
    def get_first_contact(self):
        if not self.config.first_contact:
            return
        
        return self.resolve_node(self.config.first_contact)
    
    def apply_first_contact(self, source: BaseNodeConfig, target: BaseNodeConfig):
        target.koi_net.first_contact.rid = source.koi_net.node_rid
        target.koi_net.first_contact.url = source.koi_net.node_profile.base_url
    
    def set_first_contact(self, fc_node: NodeInterface):
        print("Setting first contact...")
        if fc_node.node.config.koi_net.node_profile.node_type == NodeType.PARTIAL:
            print("Partial nodes cannot be first contacts")
            return
        
        prev_fc_node = self.get_first_contact()
        if prev_fc_node:
            if prev_fc_node == fc_node:
                print(f"First contact is already {fc_node.name}")
                return
            self.unset_first_contact(prev_fc_node)
        
        self.config.first_contact = fc_node.name
        self.config_loader.save_to_yaml()
        
        mutated_nodes: int = 0
        for node in self.nodes:
            if node is fc_node:
                continue
            
            with node.mutate_config() as config:
                self.apply_first_contact(
                    source=fc_node.node.config,
                    target=config
                )
                mutated_nodes += 1
        
        print(f"Updated configuration of {mutated_nodes} node(s)")
    
    def unset_first_contact(self, fc_node: NodeInterface):
        print("Unsetting first contact...")
        if not self.config.first_contact:
            return
        
        self.config.first_contact = None
        self.config_loader.save_to_yaml()
        
        mutated_nodes: int = 0
        for node in self.nodes:
            with node.mutate_config() as config:
                if config.koi_net.first_contact.rid == fc_node.node.config.koi_net.node_rid:
                    config.koi_net.first_contact.rid = None
                    config.koi_net.first_contact.url = None
                    mutated_nodes += 1
        
        print(f"Updated configuration of {mutated_nodes} node(s)")

    def sync(self):
        fc_node = self.get_first_contact()
        if fc_node and not fc_node.exists():
            fc_node.create()
            
        for node in self.nodes:
            if not node.exists():
                node.create()
            
            if fc_node and node is not fc_node:
                with node.mutate_config() as config:
                    self.apply_first_contact(
                        source=fc_node.node.config,
                        target=config
                    )
    
    def wipe(self):
        for node in self.nodes:
            if node.exists():
                node.wipe()

    def run(self):
        try:
            self.start()
            
            print(f"Completed startup of {len(self.nodes)} node(s)!")
            print("Press Ctrl + C to quit")
            while any(n.state() is NodeState.RUNNING for n in self.nodes):
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            pass
        
        finally:
            self.stop()
    
    def start(self):
        for name in self.config.nodes:
            node = self.resolve_node(name)
            if node.state() == NodeState.IDLE:
                node.start()
            
    def stop(self):
        for name in reversed(self.config.nodes):
            node = self.resolve_node(name)
            if node.state() == NodeState.RUNNING:
                node.stop()
        
