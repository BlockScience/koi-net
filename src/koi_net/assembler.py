import inspect
from enum import StrEnum
from typing import Any, Protocol
from dataclasses import make_dataclass

import structlog
from pydantic import BaseModel

from .entrypoints.base import EntryPoint

log = structlog.stdlib.get_logger()


class CompType(StrEnum):
    FACTORY = "FACTORY"
    OBJECT = "OBJECT"

class BuildOrderer(type):
    def __new__(cls, name: str, bases: tuple, dct: dict[str]):
        """Sets `cls._build_order` from component order in class definition."""
        cls = super().__new__(cls, name, bases, dct)
        
        if "_build_order" not in dct:
            components: dict[str, Any] = {}
            # adds components from base classes (including cls)
            for base in reversed(inspect.getmro(cls)[:-1]):
                for k, v in vars(base).items():
                    # excludes built in and private attributes
                    if not k.startswith("_"):
                        components[k] = v
                        
            # recipe list constructed from names of non-None components
            cls._build_order = [
                name for name, _type in components.items()
                if _type is not None
            ]
            
        return cls

class NodeContainer(Protocol):
    """Dummy 'shape' for node containers built by assembler."""
    entrypoint = EntryPoint

class NodeAssembler(metaclass=BuildOrderer):    
    def __new__(self) -> NodeContainer:
        """Returns assembled node container."""
        return self._build()
    
    @classmethod
    def _build_deps(
        cls, 
        build_order: list[str]
    ) -> dict[str, tuple[CompType, list[str]]]:
        """Returns dependency graph for components defined in `cls_build_order`.
        
        Graph representation is a dict where each key is a component name,
        and the value is tuple containing the component type, and a list
        of dependency component names.
        """
        
        dep_graph = {}
        for comp_name in build_order:
            try:
                comp = getattr(cls, comp_name)
            except AttributeError:
                raise Exception(f"Component '{comp_name}' not found in class definition")
            
            if not callable(comp):
                comp_type = CompType.OBJECT
                dep_names = []
            
            elif isinstance(comp, type) and issubclass(comp, BaseModel):
                comp_type = CompType.OBJECT
                dep_names = []
            
            else:
                sig = inspect.signature(comp)
                comp_type = CompType.FACTORY
                dep_names = list(sig.parameters)
                
            dep_graph[comp_name] = (comp_type, dep_names)
            
        return dep_graph
        
    @classmethod
    def _visualize(cls, dep_graph) -> str:
        """Returns representation of dependency graph in Graphviz DOT language."""
        dep_graph = cls._build_deps(cls._build_order)
        
        s = "digraph G {\n"
        for node, (_, neighbors) in dep_graph.items():
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
        dep_graph: dict[str, tuple[CompType, list[str]]]
    ) -> dict[str, Any]:
        """Returns assembled components from dependency graph."""
        components: dict[str, Any] = {}
        for comp_name, (comp_type, dep_names) in dep_graph.items():
            comp = getattr(cls, comp_name, None)
            
            if comp_type == CompType.OBJECT:
                components[comp_name] = comp
            
            elif comp_type == CompType.FACTORY:
                # builds depedency dict for current component
                dependencies = {}
                for dep_name in dep_names:
                    if dep_name not in components:
                        raise Exception(f"Couldn't find required component '{dep_name}'")
                    dependencies[dep_name] = components[dep_name]
                components[comp_name] = comp(**dependencies)
        
        return components

    @classmethod
    def _build_node(cls, components: dict[str, Any]) -> NodeContainer:
        """Returns node container from components."""
        NodeContainer = make_dataclass(
            cls_name="NodeContainer",
            fields=[
                (name, type(component)) 
                for name, component
                in components.items()
            ],
            frozen=True
        )
        
        return NodeContainer(**components)
    
    @classmethod
    def _build(cls) -> NodeContainer:
        """Returns node container after calling full build process."""
        dep_graph = cls._build_deps(cls._build_order)
        comps = cls._build_comps(dep_graph)
        node = cls._build_node(comps)
        return node