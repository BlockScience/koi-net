import time
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

from ..interfaces.network import NetworkInterface


load_dotenv()


app = typer.Typer()
console = Console()

@app.command()
def list_node_types():
    network = NetworkInterface()
    
    table = Table()
    table.add_column("aliases", style="cyan")
    table.add_column("node types", style="magenta")

    for module, aliases in network.get_node_modules().items():
        table.add_row(", ".join(aliases), module)
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
def start(delay: int = 1):
    network = NetworkInterface()
    print("starting network...")
    network.start(delay=delay)
    
    try:
        while any(n.process.poll() is None for n in network.nodes.values()):
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("stopping network...")
        network.stop()
        
        for node in network.nodes.values():
            node.process.wait()
    
@app.command()
def set_first_contact(name: str, force: bool = False):
    network = NetworkInterface()

    print(f"First contact updated from '{network.config.first_contact}' -> '{name}'")
    
    network.config.first_contact = name
    network.config_loader.save_to_yaml()
    
    fc_node = network.nodes[network.config.first_contact]
    fc_config = fc_node.get_config()
    fc_rid = fc_config.koi_net.node_rid
    fc_url = fc_config.koi_net.node_profile.base_url
    
    updated_nodes = 0
    for node in network.nodes.values():
        with node.mutate_config() as n_config:
            if not force and n_config.koi_net.first_contact.rid:
                continue
            
            if node.name == network.config.first_contact:
                continue
            
            n_config.koi_net.first_contact.rid = fc_rid
            n_config.koi_net.first_contact.url = fc_url
            updated_nodes += 1
    
    print(f"Updated config for {updated_nodes} node(s)")
        