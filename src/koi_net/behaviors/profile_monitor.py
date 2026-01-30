from dataclasses import dataclass
from logging import Logger
from rid_lib.ext import Bundle

from ..build.component import depends_on
from ..identity import NodeIdentity
from ..processor.kobj_queue import KobjQueue


@dataclass
class ProfileMonitor:
    """Processes changes to node profile in the config."""
    
    log: Logger
    kobj_queue: KobjQueue
    identity: NodeIdentity
    
    @depends_on("kobj_worker", "port_manager")
    def start(self):
        self.process_profile()
        
    def process_profile(self):
        """Processes identity bundle generated from config."""
        
        self_bundle = Bundle.generate(
            rid=self.identity.rid,
            contents=self.identity.profile.model_dump()
        )
        
        self.kobj_queue.push(bundle=self_bundle)
        
        self.log.debug("Waiting for profile to be processed...")
        # IMPORTANT: this waits for the identity bundle to be processed, later 
        # components (like the handshaker) assume this exists at runtime.
        self.kobj_queue.q.join()
        self.log.debug("Done!")
        