import importlib
import inspect
import pkgutil
from importlib.metadata import entry_points

from ..core import BaseNode


ENTRY_POINT_GROUP = "koi_net.node"
MODULE_PREFIX = "koi_net_"
MODULE_POSTFIX = "_node"
MODULE_CORE = ".core"


class ModuleTracker:
    def __init__(self):
        self.module_names: set[str] = set()
        # alias -> module name
        self.alias_module_map: dict[str, str] = {}
        
        self.load_module_names()
        
    def resolve_ref(self, module_ref) -> str:
        if module_ref in self.module_names:
            module_name = module_ref
        elif module_ref in self.alias_module_map:
            module_name = self.alias_module_map[module_ref]
        else:
            raise ModuleNotFoundError(f"Couldn't resolve '{module_ref}'")
        
        return module_name
    
    def load_class(self, module_name):
        core = importlib.import_module(module_name + MODULE_CORE)
        for _, obj in inspect.getmembers(core):
            if (getattr(obj, "__module__", None) == core.__name__ 
                and issubclass(obj, BaseNode)):
                return obj
        
    def load_module_names(self):
        for ep in entry_points(group=ENTRY_POINT_GROUP):
            self.module_names.add(ep.module)
            self.alias_module_map[ep.name] = ep.module

        for module in pkgutil.iter_modules():
            if (module.name.startswith(MODULE_PREFIX) and module.name.endswith(MODULE_POSTFIX)):
                self.module_names.add(module.name)
                module_alias = module.name[len(MODULE_PREFIX):-len(MODULE_POSTFIX)]
                self.alias_module_map.setdefault(module_alias, module.name)

module_tracker = ModuleTracker()