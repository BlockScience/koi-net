
from typing import Any, Self

import structlog

from .artifact import AssemblyArtifact, CompType
from .container import NodeContainer

log = structlog.stdlib.get_logger()


class NodeAssembler:
    _artifact: AssemblyArtifact = None
    
    # optional order overrides:
    _start_order: list[str]
    _stop_order: list[str]
    
    # annotation hack to show the components and container methods
    def __new__(cls) -> Self | NodeContainer:
        """Returns assembled node container."""
        
        # builds assembly artifact if it doesn't exist
        if not cls._artifact:
            cls._artifact = AssemblyArtifact(cls)
            cls._artifact.build()
        
        components = cls._build_components(cls._artifact)
        
        return NodeContainer(cls._artifact, **components)
    
    @staticmethod
    def _build_components(artifact: AssemblyArtifact):
        """Returns assembled components as a dict."""
        
        print("\nbuilding components")
        components: dict[str, Any] = {}
        for comp_name in artifact.init_order:
        # for comp_name, (comp_type, dep_names) in dep_graph.items():
            comp = artifact.comp_dict[comp_name]
            comp_type = artifact.comp_types[comp_name]
            
            print(comp, comp_type)
            
            if comp_type == CompType.OBJECT:
                components[comp_name] = comp
            
            elif comp_type == CompType.SINGLETON:
                # builds depedency dict for current component
                dependencies = {}
                for dep in artifact.dep_graph[comp_name]:
                    if dep not in components:
                        raise Exception(f"Couldn't find required component '{dep}'")
                    dependencies[dep] = components[dep]
                components[comp_name] = comp(**dependencies)
                
        return components
