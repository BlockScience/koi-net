from pydantic import BaseModel
from ruamel.yaml import YAML


class KoiNetworkConfig(BaseModel):
    first_contact: str | None = None
    nodes: dict[str, str] = {}

class ConfigProxy:
    """Proxy for config access.
    
    Allows initialization of this component, and updating state without
    destroying the original reference. Handled as if it were a config
    model by other classes, loaded and saved by the `ConfigLoader`.
    """
    _config: KoiNetworkConfig
    
    def __init__(self):
        self._config = None
    
    def __getattr__(self, name):
        if not self._config:
            raise RuntimeError("Proxy called before config loaded")
            
        return getattr(self._config, name)

class ConfigLoader:
    file_path: str
    file_content: str
    
    schema: type[KoiNetworkConfig]
    proxy: KoiNetworkConfig

    def __init__(
        self, 
        file_path: str,
        schema: type[KoiNetworkConfig],
        proxy: ConfigProxy
    ):
        self.file_path = file_path
        self.schema = schema
        self.proxy = proxy
        
        self.load_from_yaml()
    
    def load_from_yaml(self):
        yaml = YAML()
        
        try:
            with open(self.file_path, "r") as f:
                self.file_content = f.read()
            config_data = yaml.load(self.file_content)
            self.proxy._config = self.schema.model_validate(config_data)
            
        except FileNotFoundError:
            self.proxy._config = self.schema()
    
    def save_to_yaml(self):
        yaml = YAML()
        
        with open(self.file_path, "w") as f:
            try:
                config_data = self.proxy._config.model_dump(mode="json")
                yaml.dump(config_data, f)
                
            except Exception as e:
                if self.file_content:
                    f.seek(0)
                    f.truncate()
                    f.write(self.file_content)
                raise e