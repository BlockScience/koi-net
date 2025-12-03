from .consts import COMP_TYPE_OVERRIDE
from .artifact import CompType

def object(cls):
    setattr(cls, COMP_TYPE_OVERRIDE, CompType.OBJECT)
    return cls

def factory(cls):
    setattr(cls, COMP_TYPE_OVERRIDE, CompType.FACTORY)