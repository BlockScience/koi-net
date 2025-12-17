import os
import shutil
from importlib.metadata import entry_points

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from koi_net.config.base import BaseNodeConfig, EnvConfig
from koi_net.core import BaseNode

from .models import KoiNetworkConfig
# from koi_net.build.container import NodeContainer

app = typer.Typer()
console = Console()

installed_nodes = entry_points(group="koi_net.node")

net_config = KoiNetworkConfig.load_from_yaml()

@app.command()
def list_node_types():
    table = Table(title="installed node types")
    table.add_column("name", style="cyan")
    table.add_column("module", style="magenta")

    for node in installed_nodes:
        table.add_row(node.name, node.module)
    console.print(table)
    
@app.command()
def list_nodes():
    table = Table(title="created nodes")
    table.add_column("name", style="cyan")
    table.add_column("rid", style="magenta")

    for dir in os.listdir('.'):
        if not os.path.isdir(dir):
            continue
        for file in os.listdir(dir):
            file_path = os.path.join(dir, file)
            if not (os.path.isfile(file_path) and file == "config.yaml"):
                continue
            
            os.chdir(dir)
            
            node_type = net_config.nodes.get(dir)
            
            ep, *_ = installed_nodes.select(name=node_type)
            NodeClass: type[BaseNode] = ep.load()
            
            config_proxy = NodeClass.config()
            NodeClass.config_loader(
                config_schema=NodeClass.config_schema,
                config=config_proxy
            )
            config_proxy: BaseNodeConfig
        
            # print(node.identity.rid)
            
            table.add_row(dir, str(config_proxy.koi_net.node_rid))
            
            os.chdir('..')
    
    console.print(table)

@app.command()
def create(node_type: str, node_name: str | None = None):
    if node_type not in list(map(lambda ep: ep.name, installed_nodes)):
        console.print(f"[bold red]Error:[/bold red] node type '{node_type}' doesn't exist")
        raise typer.Exit(code=1)

    node_name = node_name or node_type
    
    try:
        os.mkdir(node_name)
    except FileExistsError:
        console.print(f"A node with the name '{node_name}' already exists!")
        raise typer.Exit(code=1)
    
    net_config.nodes[node_name] = node_type
    net_config.save_to_yaml()
    
    init(node_name)

@app.command()
def init(node_name: str):
    os.chdir(node_name)
    
    node_type = net_config.nodes[node_name]
    
    eps = installed_nodes.select(name=node_type)
    if eps:
        ep = list(eps)[0]
        
    NodeClass: type[BaseNode] = ep.load()
    
    for _, field in NodeClass.config_schema.model_fields.items():
        field_type = field.annotation
        if issubclass(field_type, EnvConfig):
            try:
                field_type()
            except ValidationError as exc:
                console.print("Missing required environment variables:")
                for err in exc.errors():
                    if err["type"] == "missing":
                        env_var_name = err["loc"][0].upper()
                        console.print(f"\t[bold red]{env_var_name}[/bold red]")
                console.print(f"Set these variables and run [bold blue]koi init {node_name}[/bold blue] to try again")
                raise typer.Exit(code=1)
    
    node = NodeClass()
    node.config_loader.start()
    
    os.chdir('..')
    
@app.command()
def remove(name: str):
    shutil.rmtree(name)
    net_config.nodes.pop(name, None)
    net_config.save_to_yaml()
    
@app.command()
def start(name: str):
    os.chdir(name)
    node_type = net_config.nodes.get(name)
    ep = list(installed_nodes.select(name=node_type))[0]
    create_node = ep.load()
    
    create_node().run()