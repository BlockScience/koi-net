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
        
    def execute(self, *args, capture_output: bool = False):
        with contextlib.chdir(self.name):
            return subprocess.Popen(
                (sys.executable, "-m", self.module, *args),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE if capture_output else None,
                text=True)
    
    def create(self):
        print(f"Creating {self.name}...")
        try:
            os.mkdir(self.name)
        except FileExistsError:
            raise LocalNodeExistsError(f"Node of name '{self.name}' already exists")
    
    def exists(self) -> bool:
        return os.path.isdir(self.name)
    
    def init(self):
        self.execute("init")
    
    def wipe(self):
        self.execute("wipe")
        
    def get_config(self, jp: str):
        process = self.execute("config", "get", jp, capture_output=True)
        return process.stdout.read().rstrip("\n")
    
    def set_config(self, jp: str, val: str):
        subprocess.run()
    
    def delete(self):
        shutil.rmtree(self.name)
    
    def start(self, suppress_output: bool = True):
        self.process = self.execute("run")
        
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
