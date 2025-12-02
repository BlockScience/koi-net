import inspect
from collections import deque
from enum import StrEnum
from typing import Any
from pydantic import BaseModel

from koi_net.assembler_consts import COMP_TYPE_OVERRIDE, START_FUNC_NAME, START_ORDER_OVERRIDE, STOP_FUNC_NAME, STOP_ORDER_OVERRIDE


class CompType(StrEnum):
    FACTORY = "FACTORY"
    OBJECT = "OBJECT"

class AssemblyArtifact:
    assembler: Any
    comp_dict: dict[str, Any]
    dep_graph: dict[str, list[str]]
    comp_types: dict[str, CompType]
    init_order: list[str]
    start_order: list[str]
    stop_order: list[str]
    
    def __init__(self, assembler):
        self.assembler = assembler
        
    def collect_comps(self):
        """Collects components into `comp_dict` from class definition."""
        
        self.comp_dict = {}
        # adds components from class and all base classes. skips `type`, and runs in reverse so that sub classes override super class values
        for base in reversed(inspect.getmro(self.assembler)[:-1]):
            for k, v in vars(base).items():
                # excludes built in, private, and `None` attributes
                if k.startswith("_") or v is None:
                    continue
                
                self.comp_dict[k] = v
    
    def build_dependencies(self):
        """Builds dependency graph and component type map.
        
        Graph representation is an adjacency list: each key is a component 
        name, and the value is a tuple containing a list of dependency 
        component names.
        """
        
        self.comp_types = {}
        self.dep_graph = {}
        for comp_name, comp in self.comp_dict.items():
            explicit_type = getattr(comp, COMP_TYPE_OVERRIDE, None)
            
            dep_names = []
            if explicit_type:
                self.comp_types[comp_name] = explicit_type
            
            elif not callable(comp):
                self.comp_types[comp_name] = CompType.OBJECT
            
            elif isinstance(comp, type) and issubclass(comp, BaseModel):
                self.comp_types[comp_name] = CompType.OBJECT
            
            else:
                sig = inspect.signature(comp)
                self.comp_types[comp_name] = CompType.FACTORY
                dep_names = list(sig.parameters)
                
            self.dep_graph[comp_name] = dep_names
        
        [print(f"{i}: {comp_name} -> {deps}") for i, (comp_name, deps) in enumerate(self.dep_graph.items())]
    
    def build_init_order(self):
        # adj list: n -> outgoing neighbors
        
        # reverse adj list: n -> incoming neighbors
        r_adj: dict[str, list[str]] = {}
        
        # computes reverse adjacency list
        for node in self.dep_graph:
            r_adj.setdefault(node, [])
            for n in self.dep_graph[node]:
                r_adj.setdefault(n, [])
                r_adj[n].append(node)
        
        out_degree: dict[str, int] = {
            n: len(neighbors) 
            for n, neighbors in self.dep_graph.items()
        }
        
        queue = deque()
        for node in out_degree:
            if out_degree[node] == 0:
                queue.append(node)
        
        self.init_order = []
        while queue:
            n = queue.popleft()
            self.init_order.append(n)
                
            for next_n in r_adj[n]:
                out_degree[next_n] -= 1
                if out_degree[next_n] == 0:
                    queue.append(next_n)
        
        if len(self.init_order) != len(self.dep_graph):
            cycle_nodes = set(self.dep_graph.keys()) - set(self.init_order)
            raise Exception(f"Found cycle in dependency graph, the following nodes could not be ordered: {cycle_nodes}")
        
        print("\ninit order")
        [print(f"{i}: {comp_name}") for i, comp_name in enumerate(self.init_order)]
        
    def build_start_order(self):
        start_order_override = getattr(
            self.assembler, START_ORDER_OVERRIDE, None)
        
        if start_order_override:
            self.start_order = start_order_override
        else:
            self.start_order = []
            for comp_name in self.init_order:
                comp = self.comp_dict[comp_name]
                if getattr(comp, START_FUNC_NAME, None):
                    self.start_order.append(comp_name)
        
        print("\nstart order")
        [print(f"{i}: {comp_name}") for i, comp_name in enumerate(self.start_order)]
        
    def build_stop_order(self):
        stop_order_override = getattr(
            self.assembler, STOP_ORDER_OVERRIDE, None)
        
        if stop_order_override:
            self.stop_order = stop_order_override
        else:
            self.stop_order = []
            for comp_name in reversed(self.init_order):
                comp = self.comp_dict[comp_name]
                if getattr(comp, STOP_FUNC_NAME, None):
                    self.stop_order.append(comp_name)
        
        print("\nstop order")
        [print(f"{i}: {comp_name}") for i, comp_name in enumerate(self.stop_order)]
        
    
    def visualize(self) -> str:
        """Returns representation of dependency graph in Graphviz DOT language."""
        
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
        self.collect_comps()
        self.build_dependencies()
        self.build_init_order()
        self.build_start_order()
        self.build_stop_order()
        self.visualize()
