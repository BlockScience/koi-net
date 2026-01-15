import cmd
from functools import wraps

from rich.console import Console
from rich.table import Table
from rich import box

from ..build.container import NodeState
from ..log_system import LogSystem
from .exceptions import LocalNodeNotFoundError
from .module import module_interface
from .network import NetworkInterface
from .node import NodeInterface

class KoiShell(cmd.Cmd):
    # intro = "Welcome to the KOI shell, type help for a list of commands.\n"
    prompt = ">=> "
    file = None
    
    def __init__(self):
        super().__init__()
        LogSystem(use_console_handler=False)
        self.console = Console()
        
        self.console.print("KOI shell: [cyan]type `help` for a list of commands[/cyan]")
        
        self.network = NetworkInterface()
        self.console.print(f"Loaded [green]{len(module_interface.module_names)} module(s)[/green] and [green]{len(self.network.nodes)} node(s)[/green]")
        print()
        
    @staticmethod
    def load_node(func):
        @wraps(func)
        def wrapper(self: "KoiShell", name: str, *args, **kwargs):
        
            node = self.network.resolve_node(name)
            if node:
                return func(self, node, *args, **kwargs)
            else:
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
        if all(not node.initialized or node.state() == NodeState.IDLE for node in self.network.nodes):
            return True
        print("Nodes are still running! Run `network stop` first, or `QUIT` to exit anyway.")
        
    def do_QUIT(self, arg: str):
        self.network.stop()
        return True
    
    def do_help(self, subcmd: str):
        table = Table("command", "arguments", "info", box=box.SIMPLE)
        match subcmd:
            case "node":
                cmd_help = [
                    ("add", r"<module ref> \[name]", "adds a new node of type <module ref> to the network, if unset, name defaults to <module ref>"),
                    ("rm", "<name>", "removes a node from the network"),
                    # ("init", "<name>", "initializes a node"),
                    ("wipe", "<name>", "wipes a node's RID cache"),
                    
                    ("run", "<name>", "runs a node in the foreground"),
                    ("start", "<name>", "starts a node in the background"),
                    ("stop", "<name>", "stops a running background node"),
                    
                    ("list", "", "lists all nodes in the network"),
                    ("modules", "", "lists all available node modules and their aliases")
                ]
            case "network":
                cmd_help = [
                    ("run", "", "runs all network nodes in the foreground"),
                    ("start", "", "starts all network nodes in the backround"),
                    ("stop", "", "stops all running background nodes"),
                    ("state", "", "lists the current state of all network nodes"),
                    ("sync", "", "synchronizes the local environment with the network configuration")
                ]
            case _:
                cmd_help = [
                    ("node", "<sub cmd>", "group of node commands"),
                    ("network", "<sub cmd>", "group of network commands"),
                    ("help", r"\[cmd]", "list available commands or subcommands"),
                    ("quit", "", "exits the shell"),
                    ("QUIT", "", "exits the shell, even if nodes are running")
                ]
        
        for cmd_info in cmd_help:
            table.add_row(*cmd_info)
        
        self.console.print(table)
    
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
                self.module_list()
            # case "init":
            #     self.node_init(*args)
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
                
    @parse_args
    def do_module(self, sub_cmd: str, *args):
        match sub_cmd:
            case "list":
                self.module_list()
            case _:
                print(f"Unknown subcommand '{sub_cmd}'")
            
    
    def node_add(self, module_ref: str, name: str | None = None):
        name = name or module_ref
        if self.network.resolve_node(name):
            print(f"Node with name '{name}' already exists")
        
        try:
            node = NodeInterface.from_ref(name, module_ref)
        except ModuleNotFoundError as err:
            print(err)
            return
        
        if not node.exists():
            node.create()
            
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
        table = Table("name", "module", "rid", box=box.SIMPLE)
        for node in self.network.nodes:
            if not node.exists():
                continue
            
            node_rid = node.node.config.koi_net.node_rid
            table.add_row(node.name, node.module, str(node_rid))
        self.console.print(table)
            
    def module_list(self):
        table = Table("module", "alias(es)", box=box.SIMPLE)
        module_alias_map: dict[str, set[str]] = {}
        for alias, module in module_interface.alias_module_map.items():
            module_alias_map.setdefault(module, set()).add(alias)
        
        for module, alias_set in module_alias_map.items():
            table.add_row(module, ','.join(alias_set))
            
        self.console.print(table)
        
    def module_reload(self, module_ref: str):
        try:
            module = module_interface.resolve_ref(module_ref)
        except ModuleNotFoundError:
            self.console.print(f"Couldn't resolve module reference '{module_ref}'")
        
        # can only reload modules of nodes at rest
        
        for node in self.network.nodes:
            if node.state() != NodeState.IDLE:
                self.console.print(f"Skipping running node '{node.name}'")
                continue
            
            # node.load_module
        
    
    # @load_node
    # def node_init(self, node: NodeInterface):
    #     node.init()
    
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