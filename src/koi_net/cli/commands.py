import time
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

from koi_net.cli.exceptions import LocalNodeNotFoundError

from . import utils
from .interfaces.network import NetworkInterface
from .interfaces.node import MissingEnvVariablesError, LocalNodeExistsError, NodeInterface

load_dotenv()


app = typer.Typer()
node = typer.Typer()
network = typer.Typer()
app.add_typer(node, name="node")
app.add_typer(network, name="net")

console = Console()

net_if = NetworkInterface()


@node.command()
def add(module_ref: str, name: str = None, config_only: bool = False):
    name = name or module_ref
    
    try:
        module = utils.qualify_module_ref(module_ref)
        node = NodeInterface(name, module)
        try:
            node.create()
        except LocalNodeExistsError:
            console.print(f"Node '{name}' already exists")
        node.init()
        net_if.add_node(node)
    except ModuleNotFoundError:
        console.print(f"[red]Node module '{module_ref}' not found[/red]")
        raise typer.Exit(code=1)
    
@node.command()
def init(name: str):
    try:
        node = net_if.load_node(name)
        node.init()
        
    except Exception:
        console.print(f"[red]Node '{name}' doesn't exist[/red]")
        return
    
    # console.print(f"Run [cyan]koi node init {name}[/cyan] after setting")
    
@node.command()
def rm(name: str):
    node = net_if.load_node(name)
    
    if node.exists():
        node.delete()
    
    net_if.remove_node(node)
    
@node.command()
def wipe(name: str):
    net_if.load_node(name).wipe()
    
@node.command()
def run(name: str, verbose: bool = False):
    node = net_if.load_node(name)
    node.run(verbose=verbose)
    
@node.command()
def list():
    table = Table(title="created nodes")
    table.add_column("name", style="cyan")
    table.add_column("module", style="magenta")
    table.add_column("rid", style="green")

    for node in net_if.load_nodes():
        print(f"loaded {node.name}")
        if not node.exists():
            continue
        
        node_rid = node.get_config("/koi_net/node_rid")
        print("got config")
        table.add_row(node.name, node.module, node_rid)
        
    console.print(table)

@node.command()
def modules():
    table = Table()
    table.add_column("alias(es)", style="cyan")
    table.add_column("module", style="magenta")

    for module, aliases in utils.get_node_modules().items():
        table.add_row(", ".join(aliases), module)
    console.print(table)
    
    
@network.command()
def sync():
    net_if.sync()

@network.command()
def run():
    net_if.run()

# @network.command()
# def set_first_contact(name: str, force: bool = False):
#     network = NetworkInterface()

#     print(f"First contact updated from '{network.config.first_contact}' -> '{name}'")
    
#     network.config.first_contact = name
#     network.config_loader.save_to_yaml()
    
#     fc_node = network.nodes[network.config.first_contact]
#     fc_config = fc_node.get_config()
#     fc_rid = fc_config.koi_net.node_rid
#     fc_url = fc_config.koi_net.node_profile.base_url
    
#     """
#     (as coordinator)
#     python -m koi_net_coordinator_node config get /koi_net/node_rid
#     `orn:koi-net.node:coordinator+...`
    
#     [for node in nodes]
#     python -m koi_net_node config set /koi_net/first_contact/rid orn:koi-net.node
#     """
    
#     updated_nodes = 0
#     for node in network.nodes.values():
#         with node.mutate_config() as n_config:
#             if not force and n_config.koi_net.first_contact.rid:
#                 continue
            
#             if node.name == network.config.first_contact:
#                 continue
            
#             n_config.koi_net.first_contact.rid = fc_rid
#             n_config.koi_net.first_contact.url = fc_url
#             updated_nodes += 1
    
#     print(f"Updated config for {updated_nodes} node(s)")
        