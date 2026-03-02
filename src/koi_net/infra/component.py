from enum import StrEnum

from .consts import COMPONENT_TYPE_FIELD, DEPENDS_ON_FIELD


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