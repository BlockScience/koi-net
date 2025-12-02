from rid_lib.ext import Bundle
from koi_net.identity import NodeIdentity
from koi_net.processor.kobj_queue import KobjQueue


class SelfStart:
    def __init__(
        self,
        kobj_queue: KobjQueue,
        identity: NodeIdentity
    ):
        self.kobj_queue = kobj_queue
        self.identity = identity
        
    def start(self):
        print(self.identity.rid)
        print(self.identity.profile)
        
        self_bundle = Bundle.generate(
            rid=self.identity.rid,
            contents=self.identity.profile.model_dump()
        )
        
        self.kobj_queue.push(bundle=self_bundle)
        
        # will freeze if called before kobj worker is started:
        # self.kobj_queue.q.join()