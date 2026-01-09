import os
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any

import typer
from pydantic import ValidationError
from jsonpointer import JsonPointer
from rich.console import Console
from rich.panel import Panel
from ..module_tracker import module_tracker

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
        self.container = self.node_class(root_dir=Path(self.name))
        
        self.console = Console()
    
    def create(self):
        try:
            os.mkdir(self.name)
        except FileExistsError:
            pass
    
    def exists(self):
        return os.path.isdir(self.name)
    
    def delete(self):
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
        
    def run(self):
        self.container.run()
        
    def start(self):
        self.container.start()
        
    def stop(self):
        self.container.stop()
        
    def wipe(self):
        self.container.cache.drop()
        
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
    
    # @property
    # def app(self) -> typer.Typer:
    #     app = typer.Typer()
    #     config = typer.Typer()
    #     app.add_typer(config, name=CONFIG)
        
    #     app.command(INIT)(self.init)
    #     app.command(RUN)(self.run)
    #     app.command(WIPE)(self.wipe)
         
    #     @config.command(GET)
    #     def config_get(jp: str):
    #         val = self.config_get(jp)
    #         if val is not None:
    #             print(val)
        
    #     @config.command(SET)
    #     def config_set(jp: str, val: str):
    #         self.config_set(jp, val)
        
    #     @config.command(UNSET)
    #     def config_unset(jp: str):
    #         self.config_unset(jp)
            
    #     return app