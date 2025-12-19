import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

from .network import NetworkInterface
from .node import MissingEnvVariablesError, NodeExistsError


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
    
@app.command()
def network_start():
    network = NetworkInterface()
    network.start()
    
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
        