import os
from typing import TypeVar
from ruamel.yaml import YAML
from koi_net.protocol.node import NodeProfile
from rid_lib.types import KoiNetNode
from pydantic import BaseModel, Field, PrivateAttr
from dotenv import load_dotenv


class ServerConfig(BaseModel):
    host: str | None = "127.0.0.1"
    port: int | None = 8000
    path: str | None = None
    
    @property
    def url(self):
        return f"http://{self.host}:{self.port}{self.path or ''}"

class KoiNetConfig(BaseModel):
    node_name: str
    node_rid: KoiNetNode | None = None
    node_profile: NodeProfile
    
    cache_directory_path: str | None = ".rid_cache"
    event_queues_path: str | None = "event_queues.json"

    first_contact: str | None = None

class EnvConfig(BaseModel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        load_dotenv()
    
    def __getattribute__(self, name):
        value = super().__getattribute__(name)
        if name in type(self).model_fields:
            env_val = os.getenv(value)
            if env_val is None:
                raise ValueError(f"Required environment variable {value} not set")
            return env_val
        return value

class Config(BaseModel):
    server: ServerConfig | None = Field(default_factory=ServerConfig)
    koi_net: KoiNetConfig
    _file_path: str = PrivateAttr(default="config.yaml")
    _file_content: str | None = PrivateAttr(default=None)
    
    @classmethod
    def load_from_yaml(
        cls, 
        file_path: str | None = None, 
        generate_missing: bool = True
    ):
        yaml = YAML()
        
        try:
            with open(file_path, "r") as f:
                file_content = f.read()
            config_data = yaml.load(file_content)
            config = cls.model_validate(config_data)
            config._file_content = file_content
            
        except FileNotFoundError:
            config = cls()
            
        config._file_path = file_path
        
        if generate_missing:            
            config.koi_net.node_rid = (
                config.koi_net.node_rid or KoiNetNode.generate(config.koi_net.node_name)
            )   
            config.koi_net.node_profile.base_url = (
                config.koi_net.node_profile.base_url or config.server.url
            )
                
            config.save_to_yaml()
                    
        return config
    
    def save_to_yaml(self):
        yaml = YAML()
        
        with open(self._file_path, "w") as f:
            try:
                config_data = self.model_dump(mode="json")
                yaml.dump(config_data, f)
            except Exception as e:
                if self._file_content:
                    f.seek(0)
                    f.truncate()
                    f.write(self._file_content)
                raise e
                
ConfigType = TypeVar("ConfigType", bound=Config)
