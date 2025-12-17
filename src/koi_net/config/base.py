import structlog
from pydantic import BaseModel, Field, model_validator

from ..build import comp_type
from ..protocol.secure import PrivateKey
from .env_config import EnvConfig
from .koi_net_config import KoiNetConfig

log = structlog.stdlib.get_logger()


@comp_type.object
class BaseNodeConfig(BaseModel):
    """Base node config class, intended to be extended.
    
    Using the `comp_type.object` decorator to mark this class as an
    object to be treated "as is" rather than attempting to initialize it
    during the build.
    """
    
    koi_net: KoiNetConfig
    # note: EnvConfig has to use a default factory, otherwise it will
    # evaluated during the library import and cause an error if any
    # env variables are undefined
    env: EnvConfig = Field(default_factory=EnvConfig)
    
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