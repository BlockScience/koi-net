from typing import Any
from pydantic import ValidationError
from jsonpointer import JsonPointer
from rich.console import Console
from rich.panel import Panel

import typer

from koi_net.build.container import NodeContainer
from koi_net.core import BaseNode
from koi_net.config.env_config import EnvConfig
from .exceptions import MissingEnvVariablesError

class NodeModuleInterface:
    def __init__(self, node_class: type[BaseNode], suppress_output: bool = False):
        self.node_class = node_class
        self._node = None
        self.console = Console()
        self.suppress_output = suppress_output
    
    @property
    def node(self) -> BaseNode | NodeContainer:
        if not self._node:
            self._node = self.node_class(
            # use_console_handler=False
            # setup CLI mode here
        )
        return self._node
    
    def run(self):
        self.node.run()
        
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
        
        self.node.config_loader.start()
        self.console.print(f"Initialized '{self.node.identity.rid}'")
        
    def wipe(self):
        self.node.cache.drop()
        
    def config_get(self, jp: str) -> Any:
        config_json = self.node.config.model_dump()
        return JsonPointer(jp).get(config_json)
    
    def config_set(self, jp: str, val: Any):
        data = self.node.config.model_dump()
        JsonPointer(jp).set(data, val)
        config = self.node.config_schema.model_validate(data)
        self.node.config._set_delegate(config)
        self.node.config_loader.save_to_yaml()
        
    def config_unset(self, jp: str):
        self.config_set(jp, None)
    
    @property
    def app(self) -> typer.Typer:
        app = typer.Typer()
        config = typer.Typer()
        app.add_typer(config, name="config")
        
        @app.command()
        def init():
            self.init()
        
        @app.command()
        def run():
            self.run()
            
        @app.command()
        def wipe(): 
            self.wipe()
            
        @config.command("get")
        def config_get(jp: str):
            print(self.config_get(jp))
        
        @config.command("set")
        def config_set(jp: str, val: str):
            self.config_set(jp, val)
        
        @config.command("unset")
        def config_unset(jp: str):
            self.config_unset(jp)
            
        return app