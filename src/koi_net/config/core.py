import os
from pydantic import BaseModel, model_validator
from dotenv import load_dotenv
from rid_lib import RIDType
from rid_lib.types import KoiNetNode
import structlog

from ..build import comp_type
from ..protocol.secure import PrivateKey
from ..protocol.node import NodeProfile

log = structlog.stdlib.get_logger()


class EventWorkerConfig(BaseModel):
    queue_timeout: float = 0.1
    max_buf_len: int = 5
    max_wait_time: float = 1.0
    
class KobjWorkerConfig(BaseModel):
    queue_timeout: float = 0.1

class NodeContact(BaseModel):
    rid: KoiNetNode | None = None
    url: str | None = None

class KoiNetConfig(BaseModel):
    """Config for KOI-net parameters."""
    
    node_name: str
    node_rid: KoiNetNode | None = None
    node_profile: NodeProfile
    
    rid_types_of_interest: list[RIDType] = [KoiNetNode]
        
    cache_directory_path: str = ".rid_cache"
    private_key_pem_path: str = "priv_key.pem"
    
    event_worker: EventWorkerConfig = EventWorkerConfig()
    kobj_worker: KobjWorkerConfig = KobjWorkerConfig()
    
    first_contact: NodeContact = NodeContact()
    
class EnvConfig(BaseModel):
    """Config for environment variables.
    
    Values set in the config are the variables names, and are loaded
    from the environment at runtime. For example, if the config YAML
    sets `priv_key_password: "PRIV_KEY_PASSWORD"` accessing 
    `priv_key_password` would retrieve the value of `PRIV_KEY_PASSWORD`
    from the environment variables.
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

# marking this component as static, classes are implicitly treated as
# factories, but this needs to be passed as is
@comp_type.object
class NodeConfig(BaseModel):
    """Base node config class, intended to be extended."""
    
    koi_net: KoiNetConfig
    env: EnvConfig = EnvConfig()
    
    @model_validator(mode="after")
    def generate_rid_cascade(self):
        """Generates node RID if missing."""
        if self.koi_net.node_rid and self.koi_net.node_profile.public_key:
            return self
        
        log.debug("Node RID or public key not found in config, attempting to generate")
        
        try:
            # attempts to read existing private key PEM file
            with open(self.koi_net.private_key_pem_path, "r") as f:
                priv_key_pem = f.read()
                priv_key = PrivateKey.from_pem(
                    priv_key_pem,
                    password=self.env.priv_key_password)
                log.debug("Used existing private key from PEM file")
        
        except FileNotFoundError:
            # generates new private key if PEM not found
            priv_key = PrivateKey.generate()
            
            with open(self.koi_net.private_key_pem_path, "w") as f:
                f.write(priv_key.to_pem(self.env.priv_key_password))
            log.debug("Generated new private key, no PEM file found")
        
        pub_key = priv_key.public_key()
        self.koi_net.node_rid = pub_key.to_node_rid(self.koi_net.node_name)
        log.debug(f"Node RID set to {self.koi_net.node_rid}")
        
        if self.koi_net.node_profile.public_key != pub_key.to_der():
            if self.koi_net.node_profile.public_key:
                log.warning("New private key overwriting old public key!")
            
            self.koi_net.node_profile.public_key = pub_key.to_der()
        
        return self