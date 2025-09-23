import os
from rid_lib import RIDType
from ruamel.yaml import YAML
from pydantic import BaseModel, Field, PrivateAttr
from dotenv import load_dotenv
from rid_lib.ext.utils import sha256_hash
from rid_lib.types import KoiNetNode
from .protocol.secure import PrivateKey
from .protocol.node import NodeProfile, NodeType


class ServerConfig(BaseModel):
    """Config for the node server (full node only)."""
    
    host: str = "127.0.0.1"
    port: int = 8000
    path: str | None = "/koi-net"
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{self.path or ''}"

class NodeContact(BaseModel):
    rid: KoiNetNode | None = None
    url: str | None = None

class KoiNetConfig(BaseModel):
    """Config for KOI-net."""
    
    node_name: str
    node_rid: KoiNetNode | None = None
    node_profile: NodeProfile
    
    rid_types_of_interest: list[RIDType] = Field(
        default_factory=lambda: [KoiNetNode])
    
    cache_directory_path: str = ".rid_cache"
    event_queues_path: str = "event_queues.json"
    private_key_pem_path: str = "priv_key.pem"
    polling_interval: int = 5
    
    first_contact: NodeContact = Field(default_factory=NodeContact)
    
    _priv_key: PrivateKey | None = PrivateAttr(default=None)

class EnvConfig(BaseModel):
    """Config for environment variables.
    
    Values set in the config are the variables names, and are loaded
    from the environment at runtime. For example, if the config YAML
    sets `priv_key_password: PRIV_KEY_PASSWORD` accessing 
    `priv_key_password` would retrieve the value of `PRIV_KEY_PASSWORD`
    from the environment.
    """
    
    priv_key_password: str | None = "PRIV_KEY_PASSWORD"
    
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

class NodeConfig(BaseModel):
    """Base configuration class for all nodes.
    
    Designed to be extensible for custom node implementations. Classes
    inheriting from `NodeConfig` may add additional config groups.
    """
    
    server: ServerConfig = Field(default_factory=ServerConfig)
    koi_net: KoiNetConfig
    env: EnvConfig = Field(default_factory=EnvConfig)
    
    _file_path: str = PrivateAttr(default="config.yaml")
    _file_content: str | None = PrivateAttr(default=None)
    
    @classmethod
    def load_from_yaml(
        cls, 
        file_path: str = "config.yaml", 
        generate_missing: bool = True
    ):
        """Loads config state from YAML file.
        
        Defaults to `config.yaml`. If `generate_missing` is set to 
        `True`, a private key and RID will be generated if not already
        present in the config.
        """
        yaml = YAML()
        
        try:
            with open(file_path, "r") as f:
                file_content = f.read()
            config_data = yaml.load(file_content)
            config = cls.model_validate(config_data)
            config._file_content = file_content
            
        except FileNotFoundError:
            # empty_fields = {}
            # for name, field in cls.model_fields.items():
                
            #     if field.default is None or field.default_factory is None:
            # print(empty_fields)
            config = cls()
            
            
        config._file_path = file_path
        
        if generate_missing:
            if not config.koi_net.node_rid:
                priv_key = PrivateKey.generate()
                pub_key = priv_key.public_key()
                
                config.koi_net.node_rid = KoiNetNode(
                    config.koi_net.node_name,
                    sha256_hash(pub_key.to_der())
                )
                
                with open(config.koi_net.private_key_pem_path, "w") as f:
                    f.write(
                        priv_key.to_pem(config.env.priv_key_password)
                    )
                
                config.koi_net.node_profile.public_key = pub_key.to_der()
            
            if config.koi_net.node_profile.node_type == NodeType.FULL:
                config.koi_net.node_profile.base_url = (
                    config.koi_net.node_profile.base_url or config.server.url
                )
                
            config.save_to_yaml()
                    
        return config
    
    def save_to_yaml(self):
        """Saves config state to YAML file.
        
        File path is set by `load_from_yaml` class method.
        """
        
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
                
