from dataclasses import dataclass, field
from logging import Logger
from typing import TYPE_CHECKING

from rid_lib.core import RID, RIDType
from rid_lib.ext import Bundle

if TYPE_CHECKING:
    from ..effector import Effector


@dataclass
class DerefHandler:
    log: Logger
    effector: "Effector"
    
    rid_types: tuple[RIDType] = field(init=False)
    
    def __post_init__(self):
        self.effector.register_handler(self)
    
    def handle(self, rid: RID) -> Bundle | None:
        ...