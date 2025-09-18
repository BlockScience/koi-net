from rid_lib.ext import Cache
from koi_net.config import NodeConfig

class CacheProvider(Cache):
    def __init__(self, config: NodeConfig):
        self.config = config
        
    @property
    def directory_path(self):
        return self.config.koi_net.cache_directory_path