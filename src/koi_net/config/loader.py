from ruamel.yaml import YAML
from .core import NodeConfig


class ConfigLoader:
    _config: NodeConfig
    
    _file_path: str = "config.yaml"
    _file_content: str
    
    def __init__(self, config_cls: type[NodeConfig]):
        self._config_cls = config_cls
        self.load_from_yaml()
    
    def __getattr__(self, name):
        return getattr(self._config, name)
    
    def load_from_yaml(self):
        """Loads config state from YAML file."""
        yaml = YAML()
        
        try:
            with open(self._file_path, "r") as f:
                self._file_content = f.read()
            config_data = yaml.load(self._file_content)
            self._config = self._config_cls.model_validate(config_data)
        
        except FileNotFoundError:
            self._config = self._config_cls()
        
        self.save_to_yaml()
        
        
    def save_to_yaml(self):
        yaml = YAML()
        
        with open(self._file_path, "w") as f:
            try:
                config_data = self._config.model_dump(mode="json")
                yaml.dump(config_data, f)
            except Exception as e:
                if self._file_content:
                    f.seek(0)
                    f.truncate()
                    f.write(self._file_content)
                raise e