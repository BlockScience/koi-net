import contextlib
import functools
import importlib
import inspect
import os
import shutil
import subprocess
import sys
from typing import Generator
from contextlib import contextmanager

from pydantic import ValidationError

from koi_net.cli import utils
from koi_net.config.base import BaseNodeConfig
from koi_net.config.env_config import EnvConfig
from koi_net.core import BaseNode

from ..exceptions import MissingEnvVariablesError, LocalNodeExistsError


"""
entry point name -> module name -> node class, run node

node name (directory)
node type alias (entrypoint: `coordinator`)
node type name (module: `koi_net_coordinator_node`)

node name -> node type name: (stored in koi net config)
"""

CORE_MODULE = ".core"


class NodeInterface:
    def __init__(self, name: str, module: str):
        self.name = name
        self.module = module
        self.process = None
        
        self.node_class = self.load_node_class()
    
    @staticmethod
    def in_directory(fn):
        """Decorator to safely execute with a node directory."""
        @functools.wraps(fn)
        def wrapper(self: "NodeInterface", *args, **kwargs):
            with contextlib.chdir(self.name):
                return fn(self, *args, **kwargs)
        return wrapper
    
    def load_node_class(self) -> type[BaseNode]:
        core = importlib.import_module(self.module + CORE_MODULE)
        
        for _, obj in inspect.getmembers(core):
            # only look at objects defined in the module
            if getattr(obj, "__module__", None) != core.__name__:
                continue
            
            # identified node class for the module
            if issubclass(obj, BaseNode):
                return obj
    
    def create(self):
        print(f"Creating {self.name}...")
        try:
            os.mkdir(self.name)
        except FileExistsError:
            raise LocalNodeExistsError(f"Node of name '{self.name}' already exists")
    
    def exists(self) -> bool:
        return os.path.isdir(self.name)
    
    @in_directory
    def init(self):
        print(f"Initializing {self.name}...")
        for field in self.node_class.config_schema.model_fields.values():
            field_type = field.annotation
            if issubclass(field_type, EnvConfig):
                try:
                    field_type()
                except ValidationError as exc:
                    raise MissingEnvVariablesError(
                        message="Missing required environment variables",
                        vars=[
                            err["loc"][0].upper()
                            for err in exc.errors()
                            if err["type"] == "missing"
                        ]
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
            stdout=subprocess.PIPE,
            text=True
        )
        
        for line in self.process.stdout:
            if line.strip() == "READY":
                return
            elif not suppress_output:
                sys.stdout.write(line)
                sys.stdout.flush()
    
    def stop(self):
        self.process.stdin.write("STOP\n")
        self.process.stdin.flush()
        self.process.wait()
