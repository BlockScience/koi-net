from collections import deque
import inspect
from enum import StrEnum
from pprint import pp
from typing import Any, Protocol, Self
from dataclasses import make_dataclass

import structlog
from pydantic import BaseModel

log = structlog.stdlib.get_logger()


class CompType(StrEnum):
    FACTORY = "FACTORY"
    OBJECT = "OBJECT"


class BaseNodeContainer(Protocol):
    """Dummy 'shape' for node containers built by assembler."""
    _build_order: list[str]
    entrypoint: Any
    
    def run(self):
        try:
            self.start()
            self.entrypoint.run()
        except KeyboardInterrupt:
            ...
        finally:
            self.stop()
    
    def start(self):
        for comp_name in self._build_order:
            # print(comp_name)
            comp = getattr(self, comp_name)
            if getattr(comp, "start", None):
                print(f"Starting {comp_name}...")
                comp.start()
            
    def stop(self):
        for comp_name in reversed(self._build_order):
            comp = getattr(self, comp_name)
            if getattr(comp, "stop", None):
                print(f"Stopping {comp_name}...")
                comp.stop()

class NodeAssembler:
    # Self annotation lying to type checker to reflect typing set in node blueprints
    def __new__(self) -> Self:
        """Returns assembled node container."""
        
        comps = self._collect_comps()
        adj, comp_types = self._build_deps(comps)
        build_order, startup_order = self._build_order(adj)
        [print(f"{i}: {comp}") for i, comp in enumerate(build_order)]
        print(startup_order)
        components = self._build_comps(build_order, adj, comp_types)
        node = self._build_node(components, build_order)
        
        return node
    
    @classmethod
    def _collect_comps(cls) -> dict[str, Any]:
        comps = {}
        # adds components from base classes, including cls)
        for base in inspect.getmro(cls)[:-1]:
            for k, v in vars(base).items():
                # excludes built in, private, and `None` attributes
                if k.startswith("_") or v is None:
                    continue
                comps[k] = v
        return comps
    
    @classmethod
    def _build_deps(
        cls, comps: dict[str, Any]
    ) -> tuple[dict[str, list[str]], dict[str, CompType]]:
        """Returns dependency graph for components defined in `cls_build_order`.
        
        Graph representation is a dict where each key is a component name,
        and the value is tuple containing the component type, and a list
        of dependency component names.
        """
        
        comp_types = {}
        dep_graph = {}
        for comp_name in comps:
            try:
                comp = getattr(cls, comp_name)
            except AttributeError:
                raise Exception(f"Component '{comp_name}' not found in class definition")
            
            if not callable(comp):
                comp_types[comp_name] = CompType.OBJECT
                dep_names = []
            
            elif isinstance(comp, type) and issubclass(comp, BaseModel):
                comp_types[comp_name] = CompType.OBJECT
                dep_names = []
            
            else:
                sig = inspect.signature(comp)
                comp_types[comp_name] = CompType.FACTORY
                dep_names = list(sig.parameters)
                
            dep_graph[comp_name] = dep_names
            
        return dep_graph, comp_types
    
    @classmethod
    def _build_order(cls, adj: dict[str, list[str]]) -> list[str]:
        # adj list: n -> outgoing neighbors
        
        # reverse adj list: n -> incoming neighbors
        r_adj: dict[str, list[str]] = {}
        
        # computes reverse adjacency list
        for node in adj:
            r_adj.setdefault(node, [])
            for n in adj[node]:
                r_adj.setdefault(n, [])
                r_adj[n].append(node)
        
        out_degree: dict[str, int] = {
            n: len(neighbors) 
            for n, neighbors in adj.items()
        }
        
        queue = deque()
        for node in out_degree:
            if out_degree[node] == 0:
                queue.append(node)
        
        build_order: list[str] = []
        startup_order: list[str] = []
        while queue:
            n = queue.popleft()
            build_order.append(n)
            comp = getattr(cls, n)
            if getattr(comp, "start", None):
                startup_order.append(n)
                
            for next_n in r_adj[n]:
                out_degree[next_n] -= 1
                if out_degree[next_n] == 0:
                    queue.append(next_n)
        
        print(len(build_order), len(adj))
        if len(build_order) != len(adj):
            cycle_nodes = set(adj.keys()) - set(build_order)
            raise Exception(f"Found cycle in dependency graph, the following nodes could not be ordered: {cycle_nodes}")
        
        return build_order, startup_order
        
    @classmethod
    def _visualize(cls) -> str:
        """Returns representation of dependency graph in Graphviz DOT language."""
        dep_graph = cls._build_deps()
        
        s = "digraph G {\n"
        for node, neighbors in dep_graph.items():
            sub_s = node
            if neighbors:
                sub_s += f"-> {', '.join(neighbors)}"
            sub_s = sub_s.replace("graph", "graph_") + ";"
            s += " " * 4 + sub_s + "\n"
        s += "}"
        return s
        
    @classmethod
    def _build_comps(
        cls,
        build_order: list[str],
        dep_graph: dict[str, list[str]],
        comp_type: dict[str, CompType]
    ) -> dict[str, Any]:
        """Returns assembled components from dependency graph."""
        
        components: dict[str, Any] = {}
        for comp_name in build_order:
        # for comp_name, (comp_type, dep_names) in dep_graph.items():
            comp = getattr(cls, comp_name, None)
            
            if comp_type[comp_name] == CompType.OBJECT:
                components[comp_name] = comp
            
            elif comp_type[comp_name] == CompType.FACTORY:
                # builds depedency dict for current component
                dependencies = {}
                for dep in dep_graph[comp_name]:
                    if dep not in components:
                        raise Exception(f"Couldn't find required component '{dep}'")
                    dependencies[dep] = components[dep]
                components[comp_name] = comp(**dependencies)
                
        return components

    @classmethod
    def _build_node(
        cls, 
        components: dict[str, Any],
        build_order: list[str]
    ) -> BaseNodeContainer:
        """Returns node container from components."""
        
        NodeContainer = make_dataclass(
            cls_name="NodeContainer",
            fields=(("_build_order", build_order),) + tuple(
                (name, type(component))
                for name, component
                in components.items()
            ),
            bases=(BaseNodeContainer,),
            frozen=True
        )
        
        return NodeContainer(_build_order=build_order, **components)
 