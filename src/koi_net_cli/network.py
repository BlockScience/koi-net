import pkgutil
import importlib
from importlib.metadata import entry_points

from koi_net.exceptions import NodeNotFoundError
from koi_net_cli.models import ConfigLoader, ConfigProxy, KoiNetworkConfig
from koi_net_cli.node import NodeInterface

ENTRY_POINT_GROUP = "koi_net.node"
MODULE_PREFIX = "koi_net_"
MODULE_POSTFIX = "_node"


class NetworkInterface:
    def __init__(self, config_path: str = "koi-net-config.yaml"):
        self.config: KoiNetworkConfig = ConfigProxy()
        self.config_loader = ConfigLoader(
            file_path=config_path,
            schema=KoiNetworkConfig,
            proxy=self.config
        )
        
        self.nodes: dict[str, NodeInterface] = {}
        
        self.load_nodes()
    
    def load_nodes(self):
        for name, module in self.config.nodes.items():
            self.nodes[name] = NodeInterface(name, module)
    
    def start(self):
        for name, node in self.nodes.items():
            print(f"starting {name}...")
            node.start()
        
        
            
    def stop(self):
        for name, node in self.nodes.items():
            print(f"stopping {name}...")
            node.stop()
        
    def qualify_node_reference(self, node_module_ref: str) -> str | None:
        eps = entry_points(group=ENTRY_POINT_GROUP, name=node_module_ref)
        if len(eps) == 0:
            try:
                importlib.import_module(node_module_ref)
                return node_module_ref
            except ImportError:
                try:
                    expanded_ref = MODULE_PREFIX + node_module_ref + MODULE_POSTFIX
                    importlib.import_module(expanded_ref)
                    return expanded_ref
                except ImportError:
                    raise Exception(f"no node module of name '{node_module_ref}' exists")
            
        elif len(eps) == 1:
            ep, = eps
            return ep.module
        
        else:
            raise Exception("more than one endpoint with that name found")
        
    def get_node_modules(self) -> list[str]:
        return {
            ep.module for ep in entry_points(group=ENTRY_POINT_GROUP)
        } | {
            module.name for module in pkgutil.iter_modules()
            if module.name.startswith(MODULE_PREFIX) 
            and module.name.endswith(MODULE_POSTFIX)
        }
        
    def create_node(self, node_name: str, node_module_ref: str | None = None):
        node_module = self.qualify_node_reference(node_module_ref or node_name)
        
        self.nodes[node_name] = NodeInterface.create(node_name, node_module)
        
        self.config.nodes[node_name] = node_module
        self.config_loader.save_to_yaml()
        
    def delete_node(self, node_name: str):
        if node_name not in self.nodes:
            raise NodeNotFoundError(f"Node '{node_name}' not found")
        
        self.nodes[node_name].delete()
        del self.nodes[node_name]
        del self.config.nodes[node_name]
        self.config_loader.save_to_yaml()
        
        
if __name__ == "__main__":
    network = NetworkInterface()