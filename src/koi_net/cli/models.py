from typing import Generic, TypeVar
from pydantic import BaseModel
from ruamel.yaml import YAML


class KoiNetworkConfig(BaseModel):
    first_contact: str | None = None
    nodes: dict[str, str] = {}

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

class ConfigLoader:
    file_path: str
    file_content: str
    
    schema: type[KoiNetworkConfig]
    # proxy: KoiNetworkConfig

    def __init__(
        self, 
        file_path: str,
        schema: type[KoiNetworkConfig],
        proxy: ConfigProxy[KoiNetworkConfig]
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
            config = self.schema.model_validate(config_data)
            self.proxy._set_delegate(config)
            
        except FileNotFoundError:
            config = self.schema()
            self.proxy._set_delegate(config)
    
    def save_to_yaml(self):
        yaml = YAML()
        
        with open(self.file_path, "w") as f:
            try:
                config = self.proxy._get_delegate()
                config_data = config.model_dump(mode="json")
                yaml.dump(config_data, f)
                
            except Exception as e:
                if self.file_content:
                    f.seek(0)
                    f.truncate()
                    f.write(self.file_content)
                raise e
