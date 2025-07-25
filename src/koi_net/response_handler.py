import logging
from rid_lib import RID
from rid_lib.ext import Manifest, Cache
from rid_lib.ext.bundle import Bundle

from .identity import NodeIdentity
from .protocol.api_models import (
    RidsPayload,
    ManifestsPayload,
    BundlesPayload,
    FetchRids,
    FetchManifests,
    FetchBundles,
)

from .network_graph import NetworkGraph


logger = logging.getLogger(__name__)


class ResponseHandler:
    """Handles generating responses to requests from other KOI nodes."""
    
    cache: Cache
    graph: NetworkGraph
    identity: NodeIdentity
    
    def __init__(
        self, 
        cache: Cache, 
        graph: NetworkGraph, 
        identity: NodeIdentity
    ):
        self.cache = cache
        self.graph = graph
        self.identity = identity
        
    def fetch_rids(self, req: FetchRids) -> RidsPayload:
        logger.info(f"Request to fetch rids, allowed types {req.rid_types}")
        rids = self.cache.list_rids(req.rid_types)
        
        return RidsPayload(rids=rids)
        
    def fetch_manifests(self, req: FetchManifests) -> ManifestsPayload:
        logger.info(f"Request to fetch manifests, allowed types {req.rid_types}, rids {req.rids}")
        
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
        logger.info(f"Request to fetch bundles, requested rids {req.rids}")
        
        bundles: list[Bundle] = []
        not_found: list[RID] = []

        for rid in req.rids:
            bundle = self.cache.read(rid)
            if bundle:
                bundles.append(bundle)
            else:
                not_found.append(rid)
            
        return BundlesPayload(bundles=bundles, not_found=not_found)