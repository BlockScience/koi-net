import os
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
def sync():
    NetworkInterface().sync()

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
        