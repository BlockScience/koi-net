import time
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

from ..interfaces.network import NetworkInterface
from ..interfaces.node import MissingEnvVariablesError, NodeExistsError


load_dotenv()


app = typer.Typer()
console = Console()


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
    
    if network.config.first_contact == name:
        network.config.first_contact = None
        network.config_loader.save_to_yaml()
    
@app.command()
def start(name: str, verbose: bool = False):
    network = NetworkInterface()
    node = network.nodes[name]
    node.start(suppress_output=not verbose)
    try:
        while node.process.poll() is None:
            time.sleep(0.1)
    except KeyboardInterrupt:
        node.stop()
        node.process.wait()