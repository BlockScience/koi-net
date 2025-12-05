from .consts import COMP_TYPE_OVERRIDE, CompType


def object(cls):
    """Sets a component's type to `CompType.OBJECT`."""
    setattr(cls, COMP_TYPE_OVERRIDE, CompType.OBJECT)
    return cls