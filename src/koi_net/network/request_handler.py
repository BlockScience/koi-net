import logging
import httpx
from datetime import datetime, timezone, timedelta
from rid_lib import RID
from rid_lib.ext import Cache
from rid_lib.types.koi_net_node import KoiNetNode

from koi_net.identity import NodeIdentity
from koi_net.protocol.secure import PublicKey, generate_secure_payload
from koi_net.utils import sha256_hash
from ..protocol.api_models import (
    RidsPayload,
    ManifestsPayload,
    BundlesPayload,
    EventsPayload,
    FetchRids,
    FetchManifests,
    FetchBundles,
    PollEvents,
    RequestModels,
    ResponseModels
)
from ..protocol.consts import (
    BROADCAST_EVENTS_PATH,
    KOI_NET_MESSAGE_SIGNATURE,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH,
    KOI_NET_MESSAGE_SIGNATURE,
    KOI_NET_SOURCE_NODE_RID,
    KOI_NET_TARGET_NODE_RID,
    KOI_NET_TIMESTAMP
)
from ..protocol.node import NodeType
from .graph import NetworkGraph


logger = logging.getLogger(__name__)


class RequestHandler:
    """Handles making requests to other KOI nodes."""
    
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
    
    def get_url(self, node_rid: KoiNetNode) -> str:
        """Retrieves URL of a node."""
        
        node_profile = self.graph.get_node_profile(node_rid)
        if not node_profile:
            raise Exception("Node not found")
        if node_profile.node_type != NodeType.FULL:
            raise Exception("Can't query partial node")
        logger.debug(f"Resolved {node_rid!r} to {node_profile.base_url}")
        return node_profile.base_url
    
    def make_request(
        self,
        node: KoiNetNode,
        path: str, 
        request: RequestModels,
        response_model: type[ResponseModels] | None = None
    ) -> ResponseModels | None:
        url = self.get_url(node) + path
        logger.info(f"Making request to {url}")
        
        source_node = self.identity.rid
        target_node = node
        
        request_body = request.model_dump_json()
        
        secure_req_payload = generate_secure_payload(
            source_node, target_node, request_body)
        
        signature = self.identity.priv_key.sign(secure_req_payload.encode())
        
        logger.info(f"req body hash: {sha256_hash(request_body)}")
        
        headers = {
            KOI_NET_MESSAGE_SIGNATURE: signature,
            KOI_NET_SOURCE_NODE_RID: str(source_node),
            KOI_NET_TARGET_NODE_RID: str(target_node),
            KOI_NET_TIMESTAMP: datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Secure req headers {headers}")
        
        resp = httpx.post(
            url=url,
            data=request_body,
            headers=headers
        )
        
        if path == BROADCAST_EVENTS_PATH:
            logger.info("Broadcast doesn't require secure response")
            return
                
        logger.info(f"resp body hash: {sha256_hash(resp.content.decode())}")
        
        logger.info(f"Secure resp headers {resp.headers}")
        
        signature = resp.headers.get(KOI_NET_MESSAGE_SIGNATURE)
        if signature:
            source_node_rid = RID.from_string(
                resp.headers.get(KOI_NET_SOURCE_NODE_RID))
            target_node_rid = RID.from_string(
                resp.headers.get(KOI_NET_TARGET_NODE_RID))

            logger.info(f"from: {source_node_rid}")
            logger.info(f"signed: {signature}")
        
            node_profile = self.graph.get_node_profile(source_node_rid)
            
            if not node_profile:
                raise Exception("Unknown Node RID")            

            pub_key = PublicKey.from_der(node_profile.public_key)
            
            secure_resp_payload = generate_secure_payload(
                source_node_rid, target_node_rid, resp.text)
            
            if not pub_key.verify(signature, secure_resp_payload.encode()):
                raise Exception("Invalid signature")
                            
            if target_node_rid != self.identity.rid:
                raise Exception("I am not the target")
            
            # timestamp = datetime.fromisoformat(resp.headers.get(KOI_NET_TIMESTAMP))
            # if datetime.now(timezone.utc) - timestamp > timedelta(minutes=5):
            #     raise Exception("Expired message")
        
        if response_model:
            return response_model.model_validate_json(resp.text)
    
    def broadcast_events(
        self, 
        node: RID, 
        req: EventsPayload | None = None,
        **kwargs
    ) -> None:
        """See protocol.api_models.EventsPayload for available kwargs."""
        request = req or EventsPayload.model_validate(kwargs)
        self.make_request(
            node, BROADCAST_EVENTS_PATH, request
        )
        logger.info(f"Broadcasted {len(request.events)} event(s) to {node!r}")
        
    def poll_events(
        self, 
        node: RID, 
        req: PollEvents | None = None,
        **kwargs
    ) -> EventsPayload:
        """See protocol.api_models.PollEvents for available kwargs."""
        request = req or PollEvents.model_validate(kwargs)
        resp = self.make_request(
            node, POLL_EVENTS_PATH, request,
            response_model=EventsPayload
        )
        logger.info(f"Polled {len(resp.events)} events from {node!r}")
        return resp
        
    def fetch_rids(
        self, 
        node: RID, 
        req: FetchRids | None = None,
        **kwargs
    ) -> RidsPayload:
        """See protocol.api_models.FetchRids for available kwargs."""
        request = req or FetchRids.model_validate(kwargs)
        resp = self.make_request(
            node, FETCH_RIDS_PATH, request,
            response_model=RidsPayload
        )
        logger.info(f"Fetched {len(resp.rids)} RID(s) from {node!r}")
        return resp
                
    def fetch_manifests(
        self, 
        node: RID, 
        req: FetchManifests | None = None,
        **kwargs
    ) -> ManifestsPayload:
        """See protocol.api_models.FetchManifests for available kwargs."""
        request = req or FetchManifests.model_validate(kwargs)
        resp = self.make_request(
            node, FETCH_MANIFESTS_PATH, request,
            response_model=ManifestsPayload
        )
        logger.info(f"Fetched {len(resp.manifests)} manifest(s) from {node!r}")
        return resp
                
    def fetch_bundles(
        self, 
        node: RID, 
        req: FetchBundles | None = None,
        **kwargs
    ) -> BundlesPayload:
        """See protocol.api_models.FetchBundles for available kwargs."""
        request = req or FetchBundles.model_validate(kwargs)
        resp = self.make_request(
            node, FETCH_BUNDLES_PATH, request,
            response_model=BundlesPayload
        )
        logger.info(f"Fetched {len(resp.bundles)} bundle(s) from {node!r}")
        return resp