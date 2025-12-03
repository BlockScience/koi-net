from koi_net.config.core import NodeConfig


class ConfigProxy:
    """Proxy for config access.
    
    Allows initialization of this component, and updating state without
    destroying the original reference. Handled as if it were a config
    model by other classes, loaded and saved by the `ConfigLoader`.
    """
    _config: NodeConfig
    
    def __init__(self):
        self._config = None
    
    def __getattr__(self, name):
        if not self._config:
            raise Exception("Proxy called before config loaded")
            
        return getattr(self._config, name)