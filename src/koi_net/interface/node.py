import os
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any, Generator

import logging
from pydantic import ValidationError
from jsonpointer import JsonPointer
from rich.console import Console
from rich.panel import Panel

from koi_net.build.container import NodeState
from koi_net.log_system import delete_file_handler
from .module_tracker import module_tracker

from koi_net.config.env_config import EnvConfig

if TYPE_CHECKING:
    from koi_net.core import BaseNode
    from koi_net.build.container import NodeContainer


class NodeInterface:
    container: "BaseNode | NodeContainer"
    
    def __init__(
        self,
        name: str,
        module_ref: str
    ):
        self.name = name
        self.module_ref = module_ref
        
        self.module = module_tracker.resolve_ref(module_ref)
        self.node_class = module_tracker.load_class(self.module)
        self._container = None
        
        self.console = Console()
    
    @property
    def container(self):
        if not self._container:
            self._container = self.node_class(root_dir=Path(self.name))
        return self._container
    
    def create(self):
        try:
            os.mkdir(self.name)
        except FileExistsError:
            pass
    
    def exists(self):
        return os.path.isdir(self.name)
    
    def delete(self):
        delete_file_handler(self.name)
        shutil.rmtree(self.name)
        
    def init(self):
        for field in self.node_class.config_schema.model_fields.values():
            field_class = field.annotation
            if issubclass(field_class, EnvConfig):
                try:
                    field_class()
                except ValidationError as exc:
                    missing_vars = [
                        err["loc"][0].upper()
                        for err in exc.errors()
                        if err["type"] == "missing"
                    ]
                    
                    text = "\n".join([
                        f"[bold red]{v}[/bold red]" 
                        for v in missing_vars
                    ])
                    
                    self.console.print(
                        Panel.fit(
                            renderable=text, 
                            title="Cannot initialize node, missing the following enironment variables:",
                            border_style="red"))
        
        self.container.config_loader.start()
        self.console.print(f"Initialized '{self.container.identity.rid}'")
    
    def state(self):
        return self.container.get_state()
    
    def run(self):
        self.container.run()
        
    def start(self):
        if self.state() == NodeState.IDLE:
            print(f"Starting {self.name}...", end=" ", flush=True)
            self.container.start()
            print("Done")
        else:
            print("Node already started")
        
    def stop(self):
        if self.state() == NodeState.RUNNING:
            print(f"Stopping {self.name}...", end=" ", flush=True)
            self.container.stop()
            print("Done")
        else:
            print("Node already stopped")
        
    def wipe(self):
        self.container.cache.drop()
        
    def mutate_config(self):
        return self.container.config_loader.mutate()
        
    def get_config(self, jp: str) -> Any:
        config_json = self.container.config.model_dump()
        return JsonPointer(jp).get(config_json)
    
    def set_config(self, jp: str, val: Any):
        data = self.container.config.model_dump()
        pointer = JsonPointer(jp)
        prev_val = pointer.get(data)
        pointer.set(data, val)
        config = self.container.config_schema.model_validate(data)
        self.container.config._set_delegate(config)
        self.container.config_loader.save_to_yaml()
        
        val_repr = lambda v: f"'{v}'" if v is not None else "<null>"
        
        self.console.print(f"Set config value [cyan]{val_repr(prev_val)}[/cyan] -> [green]{val_repr(val)}[/green]")
        
    def unset_config(self, jp: str):
        self.set_config(jp, None)
    