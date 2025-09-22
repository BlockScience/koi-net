from pydantic import BaseModel
from rid_lib.types import KoiNetNode
from koi_net.protocol.event import Event

class End:
    """Class for a sentinel value by knowledge handlers."""
    pass

END = End()


class QueuedEvent(BaseModel):
    event: Event
    target: KoiNetNode