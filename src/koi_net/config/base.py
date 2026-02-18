from pydantic import BaseModel, Field

from ..build.component import provides, CompType
from .models import EnvConfig, KoiNetConfig


@provides(CompType.OBJECT)
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