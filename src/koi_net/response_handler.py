import logging
from rid_lib import RID
from rid_lib.ext import Manifest, Cache
from rid_lib.ext.bundle import Bundle
from rid_lib.types import KoiNetNode

from .identity import NodeIdentity
from .protocol.api_models import (
    RidsPayload,
    ManifestsPayload,
    BundlesPayload,
    FetchRids,
    FetchManifests,
    FetchBundles,
)
from .protocol.consts import (
    BROADCAST_EVENTS_PATH,
    KOI_NET_MESSAGE_SIGNATURE,
    KOI_NET_SOURCE_NODE_RID,
    KOI_NET_TARGET_NODE_RID
)
from .protocol.event import EventType
from .protocol.node import NodeProfile
from .protocol.secure import PublicKey
from .utils import sha256_hash
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
    
    def validate_request(self, headers: dict, body: bytes):
        req_signature = headers.get(KOI_NET_MESSAGE_SIGNATURE)

        logger.debug(f"req body hash: {sha256_hash(body.decode())}")
        logger.debug(f"Secure req headers {headers}")
        
        if req_signature:
            source_node_rid: KoiNetNode = RID.from_string(
                headers.get(KOI_NET_SOURCE_NODE_RID))
            target_node_rid: KoiNetNode = RID.from_string(
                headers.get(KOI_NET_TARGET_NODE_RID))
            
            node_profile = self.graph.get_node_profile(source_node_rid)
            
            if node_profile:
                pub_key = PublicKey.from_der(node_profile.public_key)
                
                if not pub_key.verify(req_signature, body):
                    raise Exception("Invalid signature")
                
                if target_node_rid != self.identity.rid:
                    raise Exception("I am not the target")
            
            else:
                raise Exception("Unknown Node RID")
        else:
            raise Exception("Missing secure headers")
               
    
    def generate_response_headers(self, resp_body: bytes, source_node_rid):
            return {
                KOI_NET_MESSAGE_SIGNATURE: self.identity.priv_key.sign(resp_body),
                KOI_NET_SOURCE_NODE_RID: str(self.identity.rid),
                KOI_NET_TARGET_NODE_RID: str(source_node_rid)
            }