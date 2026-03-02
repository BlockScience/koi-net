import cmd
import inspect
import shlex
from functools import wraps

from rich.console import Console
from rich.table import Table
from rich import box

from koi_net.infra import NodeState, LogSystem
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
        self.console.print(f"Found [green]{len(module_interface.module_names)} module(s)[/green] and [green]{len(self.network.nodes)} node(s)[/green]")
        print()
        
    def emptyline(self):
        pass
        
    @staticmethod
    def load_node(func):
        @wraps(func)
        def wrapper(self: "KoiShell", name: str, *args):
            node = self.network.resolve_node(name)
            if node:
                return func(self, node, *args)
            else:
                print(f"Could not find node '{name}'")
        return wrapper
    
    @staticmethod
    def parse_args(func):
        @wraps(func)
        def wrapper(self: "KoiShell", arg: str, *args):
            parsed_args = shlex.split(arg)
            return func(self, *parsed_args)
        return wrapper
    
    @staticmethod
    def validate_args(func):
        @wraps(func)
        def wrapper(self: "KoiShell", *args):
            sig = inspect.signature(func)
            try:
                sig.bind(self, *args)
            except TypeError as err:
                self.console.print(f"[bold red]{str(err).capitalize()}[/bold red]")
                return
            
            return func(self, *args)
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
                    ("init", "<name>", "initializes a node"),
                    ("wipe-config", "", "wipes a node's configuration, including private key"),
                    ("wipe-cache", "<name>", "wipes a node's RID cache"),
                    ("wipe-logs", "<name>", "wipes a node's logs"),
                    
                    ("config-get", "<name> <loc>", "prints the config value at the specified JSON pointer location"),
                    ("config-set", "<name> <loc> <val>", "sets the config at JSON pointer location to value"),
                    ("config-unset", "<name> <loc>", ""),
                    ("info", "<name>", "shows info about nodes edges"),
                    
                    ("run", "<name>", "runs a node in the foreground"),
                    ("start", "<name>", "starts a node in the background"),
                    ("stop", "<name>", "stops a running background node"),
                    
                    ("list", "", "lists all nodes in the network")
                ]
            case "network":
                cmd_help = [
                    ("sync", "", "synchronizes the local environment with the network configuration"),
                    ("wipe-config", "", "wipes configuration, including private key, of all network nodes"),
                    ("wipe-cache", "", "wipes RID cache of all network nodes"),
                    ("wipe-logs", "", "wipes logs of all network nodes"),
                    ("status", "", "lists the current state of all network nodes"),
                    
                    ("set-first-contact", "<name>", "Sets first contact of all nodes in the network"),
                    ("unset-first-contact", "", "Unsets first contact from all nodes in the network"),
                    
                    ("run", "", "runs all network nodes in the foreground"),
                    ("start", "", "starts all network nodes in the backround"),
                    ("stop", "", "stops all running background nodes"),
                    
                ]
            case "module":
                cmd_help = [
                    ("list", "", "lists all detected node modules"),
                ]
            case _:
                cmd_help = [
                    ("node", "<sub cmd>", "group of node commands"),
                    ("network", "<sub cmd>", "group of network commands"),
                    ("module", "<sub cmd>", "group of module commands"),
                    ("help", r"\[cmd]", "list available commands or subcommands"),
                    ("quit", "", "exits the shell"),
                    ("QUIT", "", "exits the shell, even if nodes are running"),
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
            case "init":
                self.node_init(*args)
            case "list":
                self.node_list(*args)
            case "config-get":
                self.node_config_get(*args)
            case "config-set":
                self.node_config_set(*args)
            case "config-unset":
                self.node_config_unset(*args)
            case "info":
                self.node_info(*args)
            case "wipe-config":
                self.node_wipe_config(*args)
            case "wipe-cache":
                self.node_wipe_cache(*args)
            case "wipe-logs":
                self.node_wipe_logs(*args)
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
                self.network_sync(*args)
            case "wipe-config":
                self.network_wipe_config(*args)
            case "wipe-cache":
                self.network_wipe_cache(*args)
            case "wipe-logs":
                self.network_wipe_logs(*args)
            case "status":
                self.network_status(*args)
            case "set-first-contact":
                self.network_set_first_contact(*args)
            case "unset-first-contact":
                self.network_unset_first_contact(*args)
            case "start":
                self.network_start(*args)
            case "stop":
                self.network_stop(*args)
            case "run":
                self.network_run(*args)
            case "set-first-contact":
                self.network_set_first_contact(*args)
            case _:
                print(f"Unknown subcommand '{sub_cmd}'")
                
    @parse_args
    def do_module(self, sub_cmd: str, *args):
        match sub_cmd:
            case "list":
                self.module_list(*args)
            case "reload":
                self.module_reload(*args)
            case _:
                print(f"Unknown subcommand '{sub_cmd}'")
            
    @validate_args
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
        
        if node.initialized:
            self.network.add_node(node)
    
    @validate_args
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
        
    @validate_args
    @load_node
    def node_init(self, node: NodeInterface):
        node.init()
    
    @validate_args
    def node_list(self):
        table = Table("name", "module", "rid", box=box.SIMPLE)
        for node in self.network.nodes:
            if not node.exists():
                continue
            
            node_rid = node.node.config.koi_net.node_rid
            table.add_row(node.name, node.module, str(node_rid))
        self.console.print(table)
    
    @validate_args
    @load_node
    def node_config_get(self, node: NodeInterface, loc: str):
        try:
            val = node.get_config(loc)
            self.console.print(val)
        except KeyError:
            pass
        
    @validate_args
    @load_node
    def node_config_set(self, node: NodeInterface, loc: str, val: str):
        node.set_config(loc, val)
    
    @validate_args
    @load_node
    def node_config_unset(self, node: NodeInterface, loc: str):
        node.unset_config(loc)
        
    @load_node
    def node_info(self, node: NodeInterface):
        node.info()
    
    @validate_args
    @load_node
    def node_run(self, node: NodeInterface):
        node.run()
    
    @validate_args
    @load_node
    def node_start(self, node: NodeInterface):
        node.start()
    
    @validate_args
    @load_node
    def node_stop(self, node: NodeInterface):
        node.stop()
    
    @validate_args
    @load_node
    def node_wipe_config(self, node: NodeInterface):
        node.wipe_config()
        print(f"Wiped config of '{node.name}'")
    
    @validate_args
    @load_node
    def node_wipe_cache(self, node: NodeInterface):
        node.wipe_cache()
        print(f"Wiped RID cache of '{node.name}'")
    
    @validate_args
    @load_node
    def node_wipe_logs(self, node: NodeInterface):
        node.wipe_logs()
        print(f"Wiped logs of '{node.name}'")
    
    @validate_args
    def network_sync(self):
        self.network.sync()
        
    @validate_args
    def network_wipe_cache(self):
        self.network.wipe_cache()
        
    @validate_args
    def network_wipe_logs(self):
        self.network.wipe_logs()
        
    @validate_args
    def network_wipe_config(self):
        self.network.wipe_config()
    
    @validate_args
    def network_status(self):
        table = Table("node", "state", box=box.SIMPLE)
        for node in self.network.nodes:
            node_state = node.state()
            match node_state:
                case NodeState.IDLE:
                    c = "white"
                case NodeState.STARTING:
                    c = "blue"
                case NodeState.RUNNING:
                    c = "green"
                case NodeState.STOPPING:
                    c = "red"
            
            table.add_row(node.name, f"[{c}]{node.state()}[/{c}]")
            
        self.console.print(table)
    
    @validate_args
    @load_node
    def network_set_first_contact(self, node: NodeInterface):
        self.network.set_first_contact(node)
    
    @validate_args
    def network_unset_first_contact(self):
        fc_node = self.network.get_first_contact()
        if fc_node:
            self.network.unset_first_contact(fc_node)
    
    @validate_args
    def network_run(self):
        self.network.run()
    
    @validate_args
    def network_start(self):
        self.network.start()
    
    @validate_args
    def network_stop(self):
        self.network.stop()
    
    @validate_args
    def module_list(self):
        table = Table("module", "alias(es)", box=box.SIMPLE)
        module_alias_map: dict[str, set[str]] = {}
        for alias, module in module_interface.alias_module_map.items():
            module_alias_map.setdefault(module, set()).add(alias)
        
        for module, alias_set in module_alias_map.items():
            table.add_row(module, ','.join(alias_set))
            
        self.console.print(table)
    
    @validate_args
    def module_reload(self, module_ref: str):
        try:
            module = module_interface.resolve_ref(module_ref)
        except ModuleNotFoundError:
            self.console.print(f"Couldn't resolve module reference '{module_ref}'")
        
        # can only reload modules of nodes at rest
        
        updated_node_class = module_interface.load_class(module, reload_module=True)
        
        affected_nodes = 0
        updated_nodes = 0
        for node in self.network.nodes:
            if node.module != module:
                continue
            
            affected_nodes += 1
            
            if node.state() != NodeState.IDLE:
                self.console.print(f"Skipping running node '{node.name}'")
                continue
            
            node.set_node_class(updated_node_class)
            updated_nodes += 1
        
        if affected_nodes == 0:
            self.console.print("No nodes were affected")
        else:
            self.console.print(f"Reload module for {updated_nodes}/{affected_nodes} nodes")
        
def run():
    koi_sh = KoiShell()
    
    try:
        koi_sh.cmdloop()
    except KeyboardInterrupt:
        print("\nDetected keyboard interrupt, hard quitting...")
        koi_sh.do_QUIT("")