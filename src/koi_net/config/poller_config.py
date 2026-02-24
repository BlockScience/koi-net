from pydantic import BaseModel


class PollerConfig(BaseModel):
    """Poller config for partial nodes."""
    polling_interval: int = 5