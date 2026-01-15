from contextlib import contextmanager
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import ValidationError

from koi_net.config.env_config import EnvConfig
from koi_net.exceptions import MissingEnvVarsError

from .proxy import ConfigProxy
from .base import BaseNodeConfig


T = TypeVar("T", bound=BaseNodeConfig)

class ConfigLoader(Generic[T]):
    """Loads node config from a YAML file, and proxies access to it."""
    
    file_path: str = "config.yaml"
    file_content: str
    
    schema: type[BaseNodeConfig]
    proxy: ConfigProxy | BaseNodeConfig
    root_dir: Path
    
    def __init__(self, config_schema, config, root_dir):
        self.schema = config_schema
        self.proxy = config
        self.root_dir = root_dir
        
        # this is a special case to allow config state dependent components
        # to initialize without a "lazy initialization" approach, in general
        # components SHOULD NOT execute code in their init phase
        
        self.validate_env_vars()
        self.load_from_yaml()
        
    def start(self):
        self.save_to_yaml()
    
    @contextmanager
    def mutate(self):
        yield self.proxy
        self.save_to_yaml()
        
    def validate_env_vars(self):
        for field in self.schema.model_fields.values():
            field_class = field.annotation
            if issubclass(field_class, EnvConfig):
                try:
                    field_class()
                except ValidationError as exc:
                    missing_vars = [
                        err["loc"][0].upper()
                        for err in exc.errors()
                        if err["type"] == "missing"
                    ]
                    raise MissingEnvVarsError(
                        f"Missing required vars: {','.join(v for v in missing_vars)}",
                        vars=missing_vars)
    
    def load_from_yaml(self):
        """Loads config from YAML file, or generates it if missing."""
        from ruamel.yaml import YAML
        yaml = YAML()
        
        try:
            with open(self.root_dir / self.file_path, "r") as f:
                self.file_content = f.read()
            config_data = yaml.load(self.file_content)
            config = self.schema.model_validate(config_data)
        
        except FileNotFoundError:
            config = self.schema()
        
        self.proxy._set_delegate(config)
        
    def save_to_yaml(self):
        """Saves config to YAML file."""
        from ruamel.yaml import YAML
        yaml = YAML()
        
        with open(self.root_dir / self.file_path, "w") as f:
            try:
                config = self.proxy._get_delegate()
                config_data = config.model_dump(
                    mode="json",
                    exclude={"env": True})
                yaml.dump(config_data, f)
                
            except Exception:
                # rewrites original content if YAML dump fails
                if self.file_content:
                    f.seek(0)
                    f.truncate()
                    f.write(self.file_content)
                raise