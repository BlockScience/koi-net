import time
import os
import shutil
from pathlib import Path
from typing import Any

from jsonpointer import JsonPointer, JsonPointerException
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from koi_net.exceptions import MissingEnvVarsError

from ..core import BaseNode
from ..build.container import NodeState, NodeContainer
from ..log_system import LogSystem
from .module import module_interface


class NodeInterface:
    node: BaseNode | NodeContainer
    
    def __init__(
        self,
        name: str,
        node_class: type[BaseNode]
    ):
        self.name = name
        self.node_class = node_class
        # top level module
        self.module = node_class.__module__.split(".")[0]
        self._node = None
        self.initialized = False
        
        self.console = Console()
        
    @classmethod
    def from_ref(cls, name: str, module_ref: str):
        module = module_interface.resolve_ref(module_ref)
        node_class = module_interface.load_class(module)
        return cls(name=name, node_class=node_class)
    
    @property
    def node(self):
        if not self.initialized:
            raise Exception("node not initialized")

        return self._node
    
    def set_node_class(self, node_class):
        self.node_class = node_class
        self.initialized = False
        self.init()
    
    def create(self):
        os.mkdir(self.name)
        self.init()
        if self.initialized:
            self.console.print(f"Created node '{self.node.identity.rid}'")
        else:
            self.delete()
    
    def exists(self):
        return os.path.isdir(self.name)
    
    def delete(self):
        LogSystem.delete_file_handler(self.name)
        shutil.rmtree(self.name)
        
    def init(self):
        if not self.initialized:
            try:
                self._node = self.node_class(root_dir=Path(self.name))
                self.initialized = True
            except MissingEnvVarsError as err:
                text = "\n".join([
                    f"[bold red]{v}[/bold red]" 
                    for v in err.vars
                ])
                
                self.console.print(
                    Panel.fit(
                        renderable=text, 
                        title="Cannot initialize node, missing the following enironment variables:",
                        border_style="red"))
            except Exception as err:
                print(err)
    
    def state(self):
        return self.node.get_state()
    
    def run(self):
        try:
            self.start()
            print("Press Ctrl + C to quit")
            while(self.state() is NodeState.RUNNING):
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            pass
        
        finally:
            self.stop()
        
    def start(self):
        if self.state() == NodeState.IDLE:
            print(f"Starting {self.name}...", end=" ", flush=True)
            self.node.start()
            print("Done")
        else:
            print("Node already started")
        
    def stop(self):
        if self.state() == NodeState.RUNNING:
            print(f"Stopping {self.name}...", end=" ", flush=True)
            self.node.stop()
            print("Done")
        else:
            print("Node already stopped")
        
    def wipe_cache(self):
        self.node.cache.drop()
        
    def wipe_logs(self):
        LogSystem.delete_file_handler(self.name, wipe_logs=True)
        
    def mutate_config(self):
        return self.node.config.mutate()
        
    def get_config(self, jp: str) -> Any:
        config_json = self.node.config.model_dump(mode="json")
        try:
            val = JsonPointer(jp).get(config_json)
            return val
        except JsonPointerException:
            self.console.print(f"[bold red]Location '{jp}' does not exist[/bold red]")
            raise KeyError("Invalid JSON pointer")
    
    def set_config(self, jp: str, val: Any):
        data = self.node.config.model_dump()
        pointer = JsonPointer(jp)
        prev_val = pointer.get(data)
        pointer.set(data, val)
        
        try:
            config = self.node.config_schema.model_validate(data)
        except ValidationError as err:
            self.console.print(f"[bold red]Invalid value '{val}': {err.errors()[0]['msg']}[/bold red]")
            return
            
        self.node.config._set_delegate(config)
        self.node.config.save_to_yaml()
        
        val_repr = lambda v: f"'{v}'" if v is not None else "<null>"
        
        self.console.print(f"Set config value [cyan]{val_repr(prev_val)}[/cyan] -> [green]{val_repr(val)}[/green]")
        
    def unset_config(self, jp: str):
        self.set_config(jp, None)
    