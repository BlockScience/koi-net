from ruamel.yaml import YAML
from .core import NodeConfig


class ConfigLoader:
    """Loads node config from a YAML file, and proxies access to it."""
    _config: NodeConfig
    
    _file_path: str = "config.yaml"
    _file_content: str
    
    def __init__(self, config_cls: type[NodeConfig]):
        self.load_from_yaml(config_cls)
    
    def __getattr__(self, name):
        """Proxies attribute lookups to internal config object."""
        return getattr(self._config, name)
    
    def load_from_yaml(self, config_cls: type[NodeConfig]):
        """Loads config from YAML file, or generates it if missing."""
        yaml = YAML()
        
        try:
            with open(self._file_path, "r") as f:
                self._file_content = f.read()
            config_data = yaml.load(self._file_content)
            self._config = config_cls.model_validate(config_data)
        
        except FileNotFoundError:
            self._config = config_cls()
        
        self.save_to_yaml()
        
    def save_to_yaml(self):
        """Saves config to YAML file."""
        yaml = YAML()
        
        with open(self._file_path, "w") as f:
            try:
                config_data = self._config.model_dump(mode="json")
                yaml.dump(config_data, f)
            except Exception as e:
                # rewrites original content if YAML dump fails
                if self._file_content:
                    f.seek(0)
                    f.truncate()
                    f.write(self._file_content)
                raise e