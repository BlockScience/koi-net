import contextlib
import functools
import importlib
import inspect
import os
import shutil
import signal
import subprocess
import sys
from typing import Generator
from contextlib import contextmanager

from pydantic import ValidationError

from koi_net.config.base import BaseNodeConfig
from koi_net.config.env_config import EnvConfig
from koi_net.core import BaseNode

from ..exceptions import MissingEnvVariablesError, NodeExistsError


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
            with contextlib.chdir(self.name):
                return fn(self, *args, **kwargs)
        return wrapper
    
    @property
    def node_class(self) -> type[BaseNode]:
        core = importlib.import_module(f"{self.module}.core")

        for _, obj in inspect.getmembers(core):
            # only look at objects defined in the module
            if getattr(obj, "__module__", None) != core.__name__:
                continue
            
            # identified node class for the module
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
        for field in self.node_class.config_schema.model_fields.values():
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
        
        self.node_class().config_loader.start()
    
    @in_directory
    def get_config(self) -> BaseNodeConfig:
        return self.node_class().config

    @contextmanager
    @in_directory
    def mutate_config(self) -> Generator[BaseNodeConfig, None, None]:
        node = self.node_class()
        yield node.config
        node.config_loader.save_to_yaml()
    
    @in_directory
    def wipe(self):
        self.node_class().cache.drop()
    
    def delete(self):
        if self.process and self.process.poll() is None:
            print("Can't delete node while it's running, stop it first.")
            return False
        shutil.rmtree(self.name)
        return True
    
    @in_directory
    def start(self, suppress_output: bool = True):
        self.process = subprocess.Popen(
            (sys.executable, "-m", self.module),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL if suppress_output else None,
            stderr=subprocess.DEVNULL if suppress_output else None,
            text=True
        )
    
    def stop(self):
        self.process.stdin.write("STOP\n")
        self.process.stdin.flush()

if __name__ == "__main__":
    node = NodeInterface("coordinator", "koi_net_coordinator_node")
    node.init()