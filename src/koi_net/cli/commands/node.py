import time
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

from koi_net.cli.exceptions import LocalNodeNotFoundError

from .. import utils
from ..interfaces.network import NetworkInterface
from ..interfaces.node import MissingEnvVariablesError, LocalNodeExistsError


load_dotenv()


app = typer.Typer()
console = Console()


@app.command()
def add(node_type: str, node_name: str = None, no_local: bool = False):
    node_name = node_name or node_type
    
    network = NetworkInterface()
    
    try:
        node_module = utils.qualify_module_ref(node_type)
        network.add_node(node_name, node_module, no_local)
    except ModuleNotFoundError:
        console.print(f"[red]Node type '{node_type}' not found[/red]")
        raise typer.Exit(code=1)
    except LocalNodeExistsError:
        console.print(f"[red]Node '{node_name}' already exists[/red]")
        raise typer.Exit(code=1)
    
    if not no_local:
        init(node_name)
    
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
        console.print(f"Run [cyan]koi node init {node_name}[/cyan] after setting")
    
@app.command()
def rm(name: str):
    network = NetworkInterface()
    
    try:
        network.remove_node(name)
    except LocalNodeNotFoundError:
        pass
    
    if network.config.first_contact == name:
        network.config.first_contact = None
        network.config_loader.save_to_yaml()
        
@app.command()
def wipe(name: str):
    network = NetworkInterface()
    network.nodes[name].wipe()
    
@app.command()
def start(name: str, verbose: bool = False):
    network = NetworkInterface()
    node = network.nodes[name]
    node.start(suppress_output=not verbose)
    print("started")
    try:
        while node.process.poll() is None:
            time.sleep(0.1)
    except KeyboardInterrupt:
        node.stop()
        node.process.wait()
        
@app.command()
def list():
    table = Table(title="created nodes")
    table.add_column("name", style="cyan")
    table.add_column("module", style="magenta")
    table.add_column("rid", style="green")

    for name, node in NetworkInterface().nodes.items():
        if not node.exists():
            continue
        
        node_conf = node.get_config()
        table.add_row(name, node.module, str(node_conf.koi_net.node_rid))
        
    console.print(table)

@app.command()
def modules():
    table = Table()
    table.add_column("alias(es)", style="cyan")
    table.add_column("module", style="magenta")

    for module, aliases in utils.get_node_modules().items():
        table.add_row(", ".join(aliases), module)
    console.print(table)