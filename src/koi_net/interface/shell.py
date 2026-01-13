import cmd
from functools import wraps

from ..build.container import NodeState
from ..log_system import LogSystem
from .exceptions import LocalNodeNotFoundError
from .module_tracker import module_tracker
from .network import NetworkInterface
from .node import NodeInterface

class KoiShell(cmd.Cmd):
    intro = "Welcome to the KOI shell, type help for a list of commands.\n"
    prompt = ">=> "
    file = None
    
    def __init__(self):
        super().__init__()
        LogSystem(use_console_handler=False)
        self.network = NetworkInterface()
        
    @staticmethod
    def load_node(func):
        @wraps(func)
        def wrapper(self: "KoiShell", name: str, *args, **kwargs):
            try:
                node = self.network.resolve_node(name)
                return func(self, node, *args, **kwargs)
            except LocalNodeNotFoundError:
                print(f"Could not find node '{name}'")
        return wrapper
    
    @staticmethod
    def parse_args(func):
        @wraps(func)
        def wrapper(self: "KoiShell", arg: str, *args, **kwargs):
            parsed_args = arg.split()
            return func(self, *parsed_args)
        return wrapper
        
    def do_quit(self, arg: str):
        if all(node.state() == NodeState.IDLE for node in self.network.nodes):
            return True
        print("Nodes are still running! Run `network stop` first, or `QUIT` to exit anyway.")
        
    def do_QUIT(self, arg: str):
        self.network.stop()
        return True
    
    @parse_args
    def do_node(self, sub_cmd: str, *args):
        match sub_cmd:
            case "add":
                self.node_add(*args)
            case "rm":
                self.node_rm(*args)
            case "list":
                self.node_list(*args)
            case "modules":
                self.node_modules()
            case "init":
                self.node_init(*args)
            case "wipe":
                self.node_wipe(*args)
            case "start":
                self.node_start(*args)
            case "stop":
                self.node_stop(*args)
            case "run":
                self.node_run(*args)
            case _:
                print(f"Unknown subcommand '{sub_cmd}'")
    
    @parse_args
    def do_network(self, sub_cmd: str, *args):
        match sub_cmd:
            case "sync":
                self.network_sync()
            case "state":
                self.network_state()
            case "start":
                self.network_start()
            case "stop":
                self.network_stop()
            case "run":
                self.network_run()
            case _:
                print(f"Unknown subcommand '{sub_cmd}'")
            
    
    def node_add(self, module_ref: str, name: str | None = None):
        name = name or module_ref
        if name in self.network.nodes:
            print(f"Node with name '{name}' already exists")
        
        node = NodeInterface(name, module_ref)
        
        if not node.exists():
            node.create()
            node.init()
            
        self.network.add_node(node)
    
    @load_node
    def node_rm(self, node: NodeInterface):
        if node.exists():
            if node.state() == NodeState.IDLE:
                node.delete()
                print(f"Removed node '{node.name}'")
            else:
                print(f"Node is running, run `node stop {node.name}` first")
                return
        
        self.network.remove_node(node)
        
    def node_list(self):
        for node in self.network.nodes:
            if not node.exists():
                continue
            
            node_rid = node.container.config.koi_net.node_rid
            print(f"{node.name} ({node.module}): {node_rid}")
            
    def node_modules(self):
        module_alias_map: dict[str, set[str]] = {}
        for alias, module in module_tracker.alias_module_map.items():
            module_alias_map.setdefault(module, set()).add(alias)
        
        for module, alias_set in module_alias_map.items():
            print(f"{module} ({','.join(alias_set)})")
    
    @load_node
    def node_init(self, node: NodeInterface):
        node.init()
    
    @load_node
    def node_run(self, node: NodeInterface):
        node.run()
    
    @load_node
    def node_start(self, node: NodeInterface):
        node.start()
    
    @load_node
    def node_stop(self, node: NodeInterface):
        node.stop()
    
    @load_node
    def node_wipe(self, node: NodeInterface):
        node.wipe()
        print(f"Wiped RID cache of '{node.name}'")
        
    def network_run(self):
        self.network.run()
        
    def network_start(self):
        self.network.start()
        
    def network_stop(self):
        self.network.stop()
    
    def network_state(self):
        self.network.state()
        
    def network_sync(self):
        self.network.sync()

def run():
    KoiShell().cmdloop()