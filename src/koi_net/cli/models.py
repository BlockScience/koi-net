from pydantic import BaseModel

from ..config.loader import ConfigLoader


class KoiNetworkConfig(BaseModel):
    first_contact: str | None = None
    nodes: dict[str, str] = {}

class NetworkConfigLoader(ConfigLoader):
    file_path: str = "koi-network-config.yaml"