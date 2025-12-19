from typing import Generic, TypeVar
from ruamel.yaml import YAML

from .proxy import ConfigProxy
from .base import BaseNodeConfig


T = TypeVar("T", bound=BaseNodeConfig)

class ConfigLoader(Generic[T]):
    """Loads node config from a YAML file, and proxies access to it."""
    
    file_path: str = "config.yaml"
    file_content: str
    
    schema: type[T]
    proxy: ConfigProxy[T]
    
    def __init__(
        self, 
        config_schema: type[T],
        config: ConfigProxy[T]
    ):
        self.schema = config_schema
        self.proxy = config
        
        # this is a special case to allow config state dependent components
        # to initialize without a "lazy initialization" approach, in general
        # components SHOULD NOT execute code in their init phase
        self.load_from_yaml()
        
    def start(self):
        self.save_to_yaml()
    
    def load_from_yaml(self):
        """Loads config from YAML file, or generates it if missing."""
        yaml = YAML()
        
        try:
            with open(self.file_path, "r") as f:
                self.file_content = f.read()
            config_data = yaml.load(self.file_content)
            config = self.schema.model_validate(config_data)
            self.proxy._set_delegate(config)
        
        except FileNotFoundError:
            config = self.schema()
            self.proxy._set_delegate(config)
        
    def save_to_yaml(self):
        """Saves config to YAML file."""
        yaml = YAML()
        
        with open(self.file_path, "w") as f:
            try:
                config = self.proxy._get_delegate()
                config_data = config.model_dump(mode="json")
                yaml.dump(config_data, f)
                
            except Exception:
                # rewrites original content if YAML dump fails
                if self.file_content:
                    f.seek(0)
                    f.truncate()
                    f.write(self.file_content)
                raise