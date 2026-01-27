import inspect
from collections import deque
from typing import TYPE_CHECKING, Any

import structlog

from ..exceptions import BuildError
from .component import (
    COMPONENT_TYPE_FIELD,
    DEPENDS_ON_FIELD, 
    START_FUNC_NAME, 
    STOP_FUNC_NAME,
    CompType
)

if TYPE_CHECKING:
    from .assembler import NodeAssembler

log = structlog.stdlib.get_logger()


class BuildArtifact:
    assembler: "NodeAssembler"
    
    comp_dict: dict[str, Any]
    comp_types: dict[str, CompType]
    dep_graph: dict[str, list[str]]
    start_graph: dict[str, list[str]]
    
    init_order: list[str]
    start_order: list[str]
    stop_order: list[str]
    
    def __init__(self, assembler: "NodeAssembler"):
        self.assembler = assembler
        
    def collect_components(self):
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
        self.start_graph = {}
        
        for comp_name, comp in self.comp_dict.items():
            
            dep_names = []
            
            
            explict_type = getattr(comp, COMPONENT_TYPE_FIELD, None)
            if explict_type:
                self.comp_types[comp_name] = explict_type
                
            elif not callable(comp):
                # non callable components are objects treated "as is"
                self.comp_types[comp_name] = CompType.OBJECT
            else:
                # callable components default to singletons
                self.comp_types[comp_name] = CompType.SINGLETON
            
            if self.comp_types[comp_name] == CompType.SINGLETON:
                sig = inspect.signature(comp)
                dep_names = list(sig.parameters)
                
                # difference of sets: dependencies and component names
                # non empty set indicates invalid dependency
                invalid_deps = set(dep_names) - set(self.comp_dict)
                if invalid_deps:
                    raise BuildError(f"Dependencies {invalid_deps} of component '{comp_name}' are undefined")
                
                start_func = getattr(comp, START_FUNC_NAME, None)
                if start_func:
                    start_deps = getattr(start_func, DEPENDS_ON_FIELD, [])
                    self.start_graph[comp_name] = start_deps
                    print(comp_name, "->", start_deps)
            
            self.dep_graph[comp_name] = dep_names
        
        log.debug("Built dependency graph")
    
    @staticmethod
    def topo_sort(adj: dict[str, list[str]]):
        """Topological sort of direct graph using Kahn's algorithm."""
        
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
        
        ordering = []
        while queue:
            # removes node from graph
            n = queue.popleft()
            ordering.append(n)
            
            # updates out degree for nodes dependent on this node
            for next_n in r_adj[n]:
                out_degree[next_n] -= 1
                # adds nodes now without dependencies to queue
                if out_degree[next_n] == 0:
                    queue.append(next_n)
        
        if len(ordering) != len(adj):
            cycle_nodes = set(adj) - set(ordering)
            raise BuildError(f"Found cycle in dependency graph, the following nodes could not be ordered: {cycle_nodes}")
        
        return ordering
    
    def build_stop_order(self, start_order: list[str]) -> list[str]:
        """Builds component stop order.
        
        Reverse of start order, only including components with a stop method.
        NOTE: Components defining a stop method MUST also define a start method.
        """
        
        stop_order = []
        for comp_name in reversed(start_order):
            comp = self.comp_dict[comp_name]
            if getattr(comp, STOP_FUNC_NAME, None):
                stop_order.append(comp_name)
        
        return stop_order

    @staticmethod
    def visualize(adj: dict[str, list[str]]) -> str:
        """Creates representation of dependency graph in Graphviz DOT language."""
        
        s = "digraph G {\n"
        for node, neighbors in adj.items():
            if node == "graph":
                node = "graph_"
            
            s += f"\t{node};\n"
            for n in neighbors:
                if n == "graph":
                    n = "graph_"
                
                s += f"\t{node} -> {n};\n"
        s += "}"
        return s
    
    def build(self):
        log.debug("Creating build artifact...")
        self.collect_components()
        self.build_dependencies()
        self.init_order = self.topo_sort(self.dep_graph)
        log.debug("Init order: " + " -> ".join(self.init_order))
        self.start_order = self.topo_sort(self.start_graph)
        log.debug("Start order: " + " -> ".join(self.start_order))
        self.stop_order = self.build_stop_order(self.start_order)
        log.debug("Stop order: " + " -> ".join(self.stop_order))
        log.debug("Done")
