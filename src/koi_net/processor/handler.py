from dataclasses import dataclass
from enum import StrEnum
from typing import Callable
from rid_lib import RIDType


# sentinel
STOP_CHAIN = object()

class HandlerType(StrEnum):
    RID = "rid", # guaranteed RID - decides whether to delete from cache OR validate manifest
    Manifest = "manifest", # guaranteed RID, Manifest - decides whether to validate bundle
    Bundle = "bundle", # guaranteed RID, Manifest, contents - decides whether to write to cache
    Network = "network", # occurs after cache action - decides whether to handle network
    Final = "final" # occurs after network.push - final action


@dataclass
class Handler:
    func: Callable
    handler_type: HandlerType
    rid_types: list[RIDType] | None

