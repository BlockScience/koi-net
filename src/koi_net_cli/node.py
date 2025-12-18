import functools
import importlib
import inspect
import os
import shutil
import signal
import subprocess
import sys

from pydantic import ValidationError

from koi_net.config.base import BaseNodeConfig
from koi_net.config.env_config import EnvConfig
from koi_net.core import BaseNode
from koi_net_cli.exceptions import MissingEnvVariablesError, NodeExistsError


"""
entry point name -> module name -> node class, run node

node name (directory)
node type alias (entrypoint: `coordinator`)
node type name (module: `koi_net_coordinator_node`)

node name -> node type name: (stored in koi net config)
"""

ENTRY_POINT_GROUP = "koi_net.node"



class NodeInterface:
    def __init__(self, name: str, module: str):
        self.name = name
        self.module = module
        self.process = None
        
    @staticmethod
    def in_directory(fn):
        @functools.wraps(fn)
        def wrapper(self: "NodeInterface", *args, **kwargs):
            os.chdir(self.name)
            resp = None
            try:
                resp = fn(self, *args, **kwargs)
            finally:
                os.chdir("..")
            return resp
        return wrapper
    
    def get_node_class(self) -> type[BaseNode]:
        core = importlib.import_module(f"{self.module}.core")

        for name, obj in inspect.getmembers(core):
            if getattr(obj, "__module__", None) != core.__name__:
                continue
            
            if issubclass(obj, BaseNode):
                return obj
    
    @classmethod
    def create(cls, name: str, module: str):
        try:
            os.mkdir(name)
        except FileExistsError:
            raise NodeExistsError(f"Node of name '{name}' already exists")
        
        return cls(name, module)
    
    @in_directory
    def init(self):
        node_class = self.get_node_class()
        for field in node_class.config_schema.model_fields.values():
            field_type = field.annotation
            if issubclass(field_type, EnvConfig):
                try:
                    field_type()
                except ValidationError as exc:
                    vars = [
                        err["loc"][0].upper()
                        for err in exc.errors()
                        if err["type"] == "missing"
                    ]
                    raise MissingEnvVariablesError(
                        message="Missing required environment variables",
                        vars=vars
                    )
                    
        
        node_class().config_loader.start()
    
    def delete(self):
        if self.process.poll() is None:
            print("Can't delete node while it's running, stop it first.")
            return False
        shutil.rmtree(self.name)
        return True
    
    @in_directory
    def start(self):
        self.process = subprocess.Popen((
            sys.executable, "-m", self.module
        ))
    
    def stop(self):
        try:
            self.process.send_signal(signal.SIGINT)
        except ValueError:
            self.process.send_signal(signal.CTRL_C_EVENT)

    @in_directory
    def get_config(self) -> BaseNodeConfig:
        node_class = self.get_node_class()
        config_proxy = node_class.config()
        node_class.config_loader(
            config_schema=node_class.config_schema,
            config=config_proxy
        )
        return config_proxy



if __name__ == "__main__":
    node = NodeInterface("coordinator", "koi_net_coordinator_node")
    node.init()