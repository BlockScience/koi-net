import pkgutil
import importlib
from importlib.metadata import entry_points

from .exceptions import MultipleEntrypointError

ENTRY_POINT_GROUP = "koi_net.node"
MODULE_PREFIX = "koi_net_"
MODULE_POSTFIX = "_node"


def qualify_module_ref(module_ref: str) -> str | None:
        eps = entry_points(group=ENTRY_POINT_GROUP, name=module_ref)
        if len(eps) == 0:
            try:
                importlib.import_module(module_ref)
                return module_ref
            except ImportError:
                try:
                    expanded_ref = MODULE_PREFIX + module_ref + MODULE_POSTFIX
                    importlib.import_module(expanded_ref)
                    return expanded_ref
                except ImportError:
                    raise ModuleNotFoundError(f"No node module of name '{module_ref}' found")
            
        elif len(eps) == 1:
            ep, = eps
            return ep.module
        
        else:
            raise MultipleEntrypointError(f"More than one entry point of name '{module_ref}' found")
        
def get_node_modules() -> dict[str, set[str]]:
    module_map = {
        ep.module: {ep.name} 
        for ep in entry_points(group=ENTRY_POINT_GROUP)
    }
    for module in pkgutil.iter_modules():
        if not (module.name.startswith(MODULE_PREFIX) 
            and module.name.endswith(MODULE_POSTFIX)):
            continue
        
        module_alias = module.name[len(MODULE_PREFIX):-len(MODULE_POSTFIX)]
        module_map.setdefault(module.name, set()).add(module_alias)
        
    return module_map