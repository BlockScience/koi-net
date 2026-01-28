from enum import StrEnum


START_FUNC_NAME = "start"
STOP_FUNC_NAME = "stop"

COMPONENT_TYPE_FIELD = "__component_type__"
DEPENDS_ON_FIELD = "__depends_on__"

class CompType(StrEnum):
    SINGLETON = "SINGLETON"
    OBJECT = "OBJECT"

def provides(component_type: CompType):
    def decorator(obj):
        setattr(obj, COMPONENT_TYPE_FIELD, component_type)
        return obj
    return decorator

def depends_on(*components):
    def decorator(obj):
        setattr(obj, DEPENDS_ON_FIELD, set(components))
        return obj
    return decorator