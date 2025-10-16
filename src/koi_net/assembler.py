import inspect
from typing import Protocol
from dataclasses import make_dataclass

import structlog

from .interfaces.entrypoint import EntryPoint

log = structlog.stdlib.get_logger()


class BuildOrderer(type):
    def __new__(cls, name: str, bases: tuple, dct: dict[str]):
        """Sets `cls._build_order` from component order in class definition."""
        cls = super().__new__(cls, name, bases, dct)
        
        if "_build_order" not in dct:
            components = {}
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
    entrypoint = EntryPoint

class NodeAssembler(metaclass=BuildOrderer):    
    def __new__(self) -> NodeContainer:
        return self._build()
    
    @classmethod
    def _build(cls) -> NodeContainer:
        components = {}
        for comp_name in cls._build_order:            
            comp_factory = getattr(cls, comp_name, None)
            
            if comp_factory is None:
                raise Exception(f"Couldn't find factory for component '{comp_name}'")
            
            sig = inspect.signature(comp_factory)
            
            required_comps = []
            for name, param in sig.parameters.items():
                required_comps.append((name, param.annotation))
            
            if len(required_comps) == 0:
                s = comp_name
            else:
                s = f"{comp_name} -> {', '.join([name for name, _type in required_comps])}"
            
            print(s.replace("graph", "_graph"), end=";\n")
            
            dependencies = {}
            for req_comp_name, req_comp_type in required_comps:
                if req_comp_name not in components:
                    raise Exception(f"Couldn't find required component '{req_comp_name}'")
                    
                dependencies[req_comp_name] = components[req_comp_name]
                
            components[comp_name] = comp_factory(**dependencies)
        
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
