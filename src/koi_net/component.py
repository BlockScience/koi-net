from .assembler_consts import COMP_TYPE_OVERRIDE
from .artifact import CompType

def static(cls):
    setattr(cls, COMP_TYPE_OVERRIDE, CompType.OBJECT)
    return cls