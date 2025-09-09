import os
import typer
from typing import Callable
from rich.console import Console
from rich.table import Table

from importlib.metadata import entry_points

from koi_net.cli.models import KoiNetworkConfig
from koi_net.core import NodeInterface
import shutil

app = typer.Typer()
console = Console()

installed_nodes = entry_points(group='koi_net.node')

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
            
            print(os.getcwd())
            os.chdir(dir)
            print(os.getcwd())
                        
            node_type = net_config.nodes.get(dir)
            
            ep = list(installed_nodes.select(name=node_type))[0]
            create_node: Callable[[], NodeInterface] = ep.load()
            
            node = create_node()
            
            print(ep)
            print(dir)
            print(node.identity.rid)
            
            table.add_row(dir, str(node.identity.rid))
            
            os.chdir('..')
            print(os.getcwd())
    
    console.print(table)

@app.command()
def create(type: str, name: str):
    # if name not in installed_nodes:
    #     console.print(f"[bold red]Error:[/bold red] node type '{name}' doesn't exist")
    #     raise typer.Exit(code=1)

    eps = installed_nodes.select(name=type)
    if eps:
        ep = list(eps)[0]
    
    os.mkdir(name)
    os.chdir(name)
    
    ep.load()
    
    os.chdir('..')
    
    net_config.nodes[name] = type
    net_config.save_to_yaml()
    
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
    create_node: Callable[[], NodeInterface] = ep.load()
    
    create_node().server.run()