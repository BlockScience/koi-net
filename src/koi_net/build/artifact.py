import inspect
from collections import deque
from typing import TYPE_CHECKING, Any

import structlog

from ..exceptions import BuildError
from .consts import (
    COMP_ORDER_OVERRIDE,
    COMP_TYPE_OVERRIDE, 
    START_FUNC_NAME, 
    START_ORDER_OVERRIDE, 
    STOP_FUNC_NAME, 
    STOP_ORDER_OVERRIDE,
    CompOrder,
    CompType
)

if TYPE_CHECKING:
    from .assembler import NodeAssembler

log = structlog.stdlib.get_logger()


class BuildArtifact:
    assembler: "NodeAssembler"
    comp_dict: dict[str, Any]
    dep_graph: dict[str, list[str]]
    comp_types: dict[str, CompType]
    init_order: list[str]
    start_order: list[str]
    stop_order: list[str]
    graphviz: str
    
    def __init__(self, assembler: "NodeAssembler"):
        self.assembler = assembler
        
    def collect_comps(self):
        """Collects components from class definition."""
        
        self.comp_dict = {}
        # adds components from class and all base classes. skips `type`, and runs in reverse so that sub classes override super class values
        for base in reversed(inspect.getmro(self.assembler)[:-1]):
            for k, v in vars(base).items():
                # excludes built in, private, and `None` attributes
                if k.startswith("_") or v is None:
                    continue
                
                self.comp_dict[k] = v
        log.debug(f"Collected {len(self.comp_dict)} components")
    
    def build_dependencies(self):
        """Builds dependency graph and component type map.
        
        Graph representation is an adjacency list: the key is a component 
        name, and the value is a tuple containing names of the depedencies.
        """
        
        self.comp_types = {}
        self.dep_graph = {}
        for comp_name, comp in self.comp_dict.items():
            
            dep_names = []
            
            explicit_type = getattr(comp, COMP_TYPE_OVERRIDE, None)
            if explicit_type:
                self.comp_types[comp_name] = explicit_type
            
            # non callable components are objects treated "as is"
            elif not callable(comp):
                self.comp_types[comp_name] = CompType.OBJECT
            
            # callable components default to singletons
            else:
                sig = inspect.signature(comp)
                self.comp_types[comp_name] = CompType.SINGLETON
                dep_names = list(sig.parameters)
                
                invalid_deps = set(dep_names) - set(self.comp_dict)
                if invalid_deps:
                    raise BuildError(f"Dependencies {invalid_deps} of component '{comp_name}' are undefined")
                
            self.dep_graph[comp_name] = dep_names
        
        log.debug("Built dependency graph")
    
    def build_init_order(self):
        """Builds component initialization order using Kahn's algorithm."""
        
        # adj list: n -> outgoing neighbors
        adj = self.dep_graph
        # reverse adj list: n -> incoming neighbors
        r_adj: dict[str, list[str]] = {}
        
        # computes reverse adjacency list
        for node in adj:
            r_adj.setdefault(node, [])
            for n in adj[node]:
                r_adj.setdefault(n, [])
                r_adj[n].append(node)
        
        # how many outgoing edges each node has
        out_degree = {
            n: len(neighbors) 
            for n, neighbors in adj.items()
        }
        
        # initializing queue: nodes w/o dependencies
        queue = deque()
        for node in out_degree:
            if out_degree[node] == 0:
                queue.append(node)
        
        self.init_order = []
        while queue:
            # removes node from graph
            n = queue.popleft()
            self.init_order.append(n)
            
            # updates out degree for nodes dependent on this node
            for next_n in r_adj[n]:
                out_degree[next_n] -= 1
                # adds nodes now without dependencies to queue
                if out_degree[next_n] == 0:
                    queue.append(next_n)
        
        if len(self.init_order) != len(self.dep_graph):
            cycle_nodes = set(self.dep_graph) - set(self.init_order)
            raise BuildError(f"Found cycle in dependency graph, the following nodes could not be ordered: {cycle_nodes}")
        
        log.debug(f"Resolved initialization order: {' -> '.join(self.init_order)}")
        
    def build_start_order(self):
        """Builds component start order.
        
        Checks if components define a start function in init order. Can
        be overridden by setting start order override in the `NodeAssembler`.
        """
        
        self.start_order = getattr(self.assembler, START_ORDER_OVERRIDE, None)
        
        if self.start_order:
            return
        
        workers = []
        start_order = []
        for comp_name in self.init_order:
            comp = self.comp_dict[comp_name]
            if getattr(comp, START_FUNC_NAME, None):
                if getattr(comp, COMP_ORDER_OVERRIDE, None) == CompOrder.WORKER:
                    workers.append(comp_name)
                else:
                    start_order.append(comp_name) 
        
        # order workers first
        self.start_order = workers + start_order
        
        log.debug(f"Resolved start order: {' -> '.join(self.start_order)}")
        
    def build_stop_order(self):
        """Builds component stop order.
        
        Checks if components define a stop function in init order. Can
        be overridden by setting stop order override in the `NodeAssembler`.
        """
        self.stop_order = getattr(self.assembler, STOP_ORDER_OVERRIDE, None)
        
        if self.stop_order:
            return
        
        workers = []
        stop_order = []
        for comp_name in self.init_order:
            comp = self.comp_dict[comp_name]
            if getattr(comp, STOP_FUNC_NAME, None):
                if getattr(comp, COMP_ORDER_OVERRIDE, None) == CompOrder.WORKER:
                    workers.append(comp_name)
                else:
                    stop_order.append(comp_name) 
        
        # order workers first (last)
        self.stop_order = workers + stop_order
        # reverse order from start order
        self.stop_order.reverse()
        
        log.debug(f"Resolved stop order: {' -> '.join(self.stop_order)}")

    def visualize(self) -> str:
        """Creates representation of dependency graph in Graphviz DOT language."""
        
        s = "digraph G {\n"
        for node, neighbors in self.dep_graph.items():
            sub_s = node
            if neighbors:
                sub_s += f"-> {', '.join(neighbors)}"
            sub_s = sub_s.replace("graph", "graph_") + ";"
            s += " " * 4 + sub_s + "\n"
        s += "}"
        self.graphviz = s
    
    def build(self):
        log.debug("Creating build artifact...")
        self.collect_comps()
        self.build_dependencies()
        self.build_init_order()
        self.build_start_order()
        self.build_stop_order()
        self.visualize()
        log.debug("Done")
