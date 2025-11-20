from ruamel.yaml import YAML

from koi_net.config.proxy import ConfigProxy
from .core import NodeConfig


class ConfigLoader:
    """Loads node config from a YAML file, and proxies access to it."""
    
    file_path: str = "config.yaml"
    file_content: str
    
    config_schema: type[NodeConfig]
    proxy: ConfigProxy
    
    def __init__(
        self, 
        config_schema: type[NodeConfig],
        config: ConfigProxy
    ):
        self.config_schema = config_schema
        self.proxy = config
    
    def load_from_yaml(self):
        """Loads config from YAML file, or generates it if missing."""
        yaml = YAML()
        
        try:
            with open(self.file_path, "r") as f:
                self.file_content = f.read()
            config_data = yaml.load(self.file_content)
            self.proxy._config = self.config_schema.model_validate(config_data)
        
        except FileNotFoundError:
            self.proxy._config = self.config_schema()
        
    def save_to_yaml(self):
        """Saves config to YAML file."""
        yaml = YAML()
        
        with open(self.file_path, "w") as f:
            try:
                config_data = self.proxy._config.model_dump(mode="json")
                yaml.dump(config_data, f)
                
            except Exception as e:
                # rewrites original content if YAML dump fails
                if self.file_content:
                    f.seek(0)
                    f.truncate()
                    f.write(self.file_content)
                raise e