from rid_lib import RID
from rid_lib.ext import Manifest, Cache
from rid_lib.ext.bundle import Bundle
from ..protocol.api_models import (
    RidsPayload,
    ManifestsPayload,
    BundlesPayload,
    FetchRids,
    FetchManifests,
    FetchBundles,
)

class ResponseHandler:
    cache: Cache
    
    def __init__(self, cache: Cache):
        self.cache = cache
        
    def fetch_rids(self, req: FetchRids) -> RidsPayload:
        rids = self.cache.list_rids(req.rid_types)
        
        return RidsPayload(rids=rids)
        
    def fetch_manifests(self, req: FetchManifests) -> ManifestsPayload:
        manifests: list[Manifest] = []
        not_found: list[RID] = []
        
        for rid in (req.rids or self.cache.list_rids(req.rid_types)):
            bundle = self.cache.read(rid)
            if bundle:
                manifests.append(bundle.manifest)
            else:
                not_found.append(rid)
        
        return ManifestsPayload(manifests=manifests, not_found=not_found)
        
    def fetch_bundles(self, req: FetchBundles) -> BundlesPayload:
        bundles: list[Bundle] = []
        not_found: list[RID] = []

        for rid in req.rids:
            bundle = self.cache.read(rid)
            if bundle:
                bundles.append(bundle)
            else:
                not_found.append(rid)
            
        return BundlesPayload(manifests=bundles, not_found=not_found)