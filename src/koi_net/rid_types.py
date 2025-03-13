from rid_lib.core import ORN

class KoiNetNode(ORN):
    namespace = "koi-net.node"
    
    def __init__(self, id):
        self.id = id
        
    @property
    def reference(self):
        return self.id
    
    @classmethod
    def from_reference(cls, reference):
        return cls(reference)
    

class KoiNetEdge(ORN):
    namespace = "koi-net.edge"
    
    def __init__(self, id):
        self.id = id
        
    @property
    def reference(self):
        return self.id
    
    @classmethod
    def from_reference(cls, reference):
        return cls(reference)