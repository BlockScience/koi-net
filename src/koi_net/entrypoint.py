from koi_net.config.core import NodeConfig


class EntryPoint:
    def __init__(self, config: NodeConfig):
        self.config = config
    
    def run(self): ...
    
    def initialize(self):
        self.config.load_from_yaml()