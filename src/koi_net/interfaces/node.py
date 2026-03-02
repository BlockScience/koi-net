import time
import os
import shutil
from pathlib import Path
from typing import Any

from jsonpointer import JsonPointer, JsonPointerException
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from rid_lib.types import KoiNetEdge
from koi_net.exceptions import MissingEnvVarsError
from koi_net.protocol.edge import EdgeProfile
from koi_net.core import BaseNode
from koi_net.infra import NodeState, NodeContainer, LogSystem

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
            # self.console.print("Failed to initialize, run `node init <name>` to try again")
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
                self.console.print_exception()
                
    
    def state(self):
        return self.node.get_state()
    
    def info(self):
        table = Table("rid types", "", "node", box=box.SIMPLE)
        for edge_rid in self.node.cache.list_rids(rid_types=[KoiNetEdge]):
            bundle = self.node.cache.read(edge_rid)
            edge_profile = bundle.validate_contents(EdgeProfile)
            
            if edge_profile.source == self.node.identity.rid:
                direction = "->"
                other = edge_profile.target
                
            elif edge_profile.target == self.node.identity.rid:
                direction = "<-"
                other = edge_profile.source
            
            else:
                continue
            
            table.add_row(str(edge_profile.rid_types[0]), direction, str(other))
            for rid_type in edge_profile.rid_types[1:]:
                table.add_row(str(rid_type))
            table.add_row()
        
        self.console.print(table)
            
        
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
        
    def start(self, block: bool = True):
        if self.state() == NodeState.IDLE:
            print(f"Starting {self.name}...", end=" ", flush=True)
            self.node.start(block=block)
            print("Done")
        else:
            print("Node already started")
        
    def stop(self, block: bool = True):
        if self.state() == NodeState.RUNNING:
            print(f"Stopping {self.name}...", end=" ", flush=True)
            self.node.stop(block=block)
            print("Done")
        else:
            print("Node already stopped")
    
    def wipe_config(self):
        self.node.config.wipe()
    
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
    