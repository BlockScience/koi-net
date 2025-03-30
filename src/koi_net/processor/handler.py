from dataclasses import dataclass
from enum import StrEnum
from typing import Callable
from rid_lib import RIDType


# sentinel
STOP_CHAIN = object()

class HandlerType(StrEnum):
    RID = "rid", # guaranteed RID - decides whether validate manifest OR cache delete
    Manifest = "manifest", # guaranteed Manifest - decides whether to validate bundle
    Bundle = "bundle", # guaranteed Bundle - decides whether to write to cache
    Network = "network", # guaranteed Bundle, after cache write/delete  - decides network targets
    Final = "final" # guaranteed Bundle, after network push - final action

@dataclass
class KnowledgeHandler:
    func: Callable
    handler_type: HandlerType
    rid_types: list[RIDType] | None

