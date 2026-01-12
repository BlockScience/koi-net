import cmd
from functools import wraps

from koi_net.interface.network import NetworkInterface
from koi_net.interface.node import NodeInterface
from koi_net.log_system import LogSystem

class KoiShell(cmd.Cmd):
    intro = "Welcome to the KOI shell, type help for a list of commands.\n"
    prompt = ">=> "
    file = None
    
    def __init__(self):
        super().__init__()
        LogSystem()
        self.network = NetworkInterface()
        
    @staticmethod
    def load_node(func):
        @wraps(func)
        def wrapper(self: "KoiShell", name: str, *args, **kwargs):
            node = self.network.resolve_node(name)
            return func(self, node, *args, **kwargs)
        return wrapper
        
    def do_quit(self, arg: str):
        return True
    
    def do_node(self, arg: str):
        args = arg.split()
        sub_cmd = args.pop(0)
        
        match sub_cmd:
            case "add":
                self.node_add(*args)
            case "rm":
                self.node_rm(*args)
            case "init":
                self.node_init(*args)
            case "start":
                self.node_start(*args)
            case "stop":
                self.node_stop(*args)
            case "run":
                self.node_run(*args)
    
    def node_add(self, module_ref: str, name: str | None = None):
        if name in self.network.nodes:
            raise Exception("Node already exists")
        
        node = NodeInterface(
            name=name or module_ref, 
            module_ref=module_ref)
        
        if not node.exists():
            node.create()
            node.init()
            
        self.network.add_node(node)
    
    @load_node
    def node_rm(self, node: NodeInterface):
        if node.exists():
            node.delete()
        
        self.network.remove_node(node)
    
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
        
if __name__ == "__main__":
    KoiShell().cmdloop()