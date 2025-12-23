import typer
from .commands import node, network

app = typer.Typer()
app.add_typer(node.app, name="node")
app.add_typer(network.app, name="network")