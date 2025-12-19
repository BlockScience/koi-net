from typing import Generic, TypeVar


T = TypeVar("T")

class ConfigProxy(Generic[T]):
    """Proxy for config access.
    
    Allows initialization of this component, and updating state without
    destroying the original reference. Handled as if it were a config
    model by other classes, loaded and saved by the `ConfigLoader`.
    """
    _delegate: T
    
    def __init__(self):
        object.__setattr__(self, "_delegate", None)
    
    def _set_delegate(self, delegate: T):
        object.__setattr__(self, "_delegate", delegate)
    
    def _get_delegate(self) -> T:
        delegate = object.__getattribute__(self, "_delegate")
        if delegate is None:
            raise RuntimeError("Proxy called before delegate loaded")
        return delegate
    
    def __getattr__(self, name):
        return getattr(self._get_delegate(), name)
    
    def __setattr__(self, name, value):
        delegate = self._get_delegate()
        setattr(delegate, name, value)
