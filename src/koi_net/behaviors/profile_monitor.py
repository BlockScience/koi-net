from rid_lib.ext import Bundle
from ..identity import NodeIdentity
from ..processor.kobj_queue import KobjQueue


class ProfileMonitor:
    """Processes changes to node profile in the config."""
    def __init__(
        self,
        kobj_queue: KobjQueue,
        identity: NodeIdentity
    ):
        self.kobj_queue = kobj_queue
        self.identity = identity
        
    def start(self):
        """Processes identity bundle generated from config."""
        self_bundle = Bundle.generate(
            rid=self.identity.rid,
            contents=self.identity.profile.model_dump()
        )
        
        self.kobj_queue.push(bundle=self_bundle)