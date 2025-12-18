import os
import shutil
from importlib.metadata import entry_points
import subprocess

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from koi_net.config.base import BaseNodeConfig, EnvConfig
from koi_net.core import BaseNode
from koi_net_cli.network import NetworkInterface
from koi_net_cli.node import MissingEnvVariablesError, NodeExistsError

from .models import KoiNetworkConfig
# from koi_net.build.container import NodeContainer
from dotenv import load_dotenv

load_dotenv()


app = typer.Typer()
console = Console()

@app.command()
def list_node_types():
    network = NetworkInterface()
    
    table = Table()
    table.add_column("node types", style="magenta")

    for module in network.get_node_modules():
        table.add_row(module)
    console.print(table)
    
@app.command()
def list_nodes():
    table = Table(title="created nodes")
    table.add_column("name", style="cyan")
    table.add_column("type", style="green")
    table.add_column("rid", style="magenta")

    network = NetworkInterface()
    for name, node in network.nodes.items():
        node_conf = node.get_config()
        table.add_row(name, node.module, str(node_conf.koi_net.node_rid))
        
    console.print(table)

@app.command()
def create(node_type: str, node_name: str | None = None):
    # if node_type not in list(map(lambda ep: ep.name, installed_nodes)):
    #     console.print(f"[bold red]Error:[/bold red] node type '{node_type}' doesn't exist")
    #     raise typer.Exit(code=1)
    
    node_name = node_name or node_type
    
    network = NetworkInterface()
    try:
        network.create_node(node_name, node_type)
        init(node_name)
    except NodeExistsError:
        console.print(f"[red]Node '{node_name}' already exists[/red]")
    
@app.command()
def init(node_name: str):
    network = NetworkInterface()
    
    if node_name not in network.nodes:
        console.print(f"[red]Node '{node_name}' doesn't exist[/red]")
        return
    
    try:
        node = network.nodes[node_name]
        node.init()
        node_rid = node.get_config().koi_net.node_rid
        console.print(f"Initialized node '{node_name}' as {node_rid}")
    except MissingEnvVariablesError as err:
        text = "\n".join([f"[bold red]{v}[/bold red]" for v in err.vars])
        panel = Panel.fit(
            text, 
            border_style="red",
            title="Cannot initialize node, missing the following enironment variables:")
        console.print(panel)
        console.print(f"Run [cyan]koi init {node_name}[/cyan] after setting")
    
@app.command()
def delete(name: str):
    network = NetworkInterface()
    network.delete_node(name)
    
@app.command()
def start(name: str):
    network = NetworkInterface()
    network.nodes[name].start()