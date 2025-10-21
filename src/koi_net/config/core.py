import os
from pydantic import BaseModel, model_validator
from dotenv import load_dotenv
from rid_lib import RIDType
from rid_lib.types import KoiNetNode

from koi_net.protocol.secure import PrivateKey
from ..protocol.node import NodeProfile


class NodeContact(BaseModel):
    rid: KoiNetNode | None = None
    url: str | None = None

class KoiNetConfig(BaseModel):
    """Config for KOI-net."""
    
    node_name: str
    node_rid: KoiNetNode | None = None
    node_profile: NodeProfile
    
    rid_types_of_interest: list[RIDType] = [KoiNetNode]
        
    cache_directory_path: str = ".rid_cache"
    event_queues_path: str = "event_queues.json"
    private_key_pem_path: str = "priv_key.pem"
    
    first_contact: NodeContact = NodeContact()
    
class EnvConfig(BaseModel):
    """Config for environment variables.
    
    Values set in the config are the variables names, and are loaded
    from the environment at runtime. For example, if the config YAML
    sets `priv_key_password: PRIV_KEY_PASSWORD` accessing 
    `priv_key_password` would retrieve the value of `PRIV_KEY_PASSWORD`
    from the environment.
    """
    
    priv_key_password: str = "PRIV_KEY_PASSWORD"
    
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
    koi_net: KoiNetConfig
    env: EnvConfig = EnvConfig()
    
    @model_validator(mode="after")
    def generate_rid_cascade(self):
        if not self.koi_net.node_rid:
            priv_key = PrivateKey.generate()
            pub_key = priv_key.public_key()
            
            self.koi_net.node_rid = pub_key.to_node_rid(self.koi_net.node_name)
            
            with open(self.koi_net.private_key_pem_path, "w") as f:
                f.write(priv_key.to_pem(self.env.priv_key_password))
            
            self.koi_net.node_profile.public_key = pub_key.to_der()
        return self