import logging
import httpx
from datetime import datetime, timezone, timedelta
from rid_lib import RID
from rid_lib.ext import Cache
from rid_lib.types.koi_net_node import KoiNetNode

from koi_net.identity import NodeIdentity
from koi_net.protocol.secure import PublicKey
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
                
    def make_request(
        self,
        node: KoiNetNode,
        path: str, 
        request: RequestModels,
        response_model: type[ResponseModels] | None = None
    ) -> ResponseModels | None:
        url = self.get_url(node) + path
        logger.debug(f"Making request to {url}")
        
        request_body = request.model_dump_json()
        
        headers = {
            KOI_NET_MESSAGE_SIGNATURE: self.identity.priv_key.sign(
                request_body.encode()
            ),
            KOI_NET_SOURCE_NODE_RID: str(self.identity.rid),
            KOI_NET_TARGET_NODE_RID: str(node),
            KOI_NET_TIMESTAMP: datetime.now(timezone.utc).isoformat()
        }
        
        resp = httpx.post(
            url=url,
            data=request_body,
            headers=headers
        )
        
        
        signature = resp.headers.get(KOI_NET_MESSAGE_SIGNATURE)
        if signature:
            source_node_rid = RID.from_string(
                resp.headers.get(KOI_NET_SOURCE_NODE_RID))
            target_node_rid = RID.from_string(
                resp.headers.get(KOI_NET_TARGET_NODE_RID))

            print("from:", source_node_rid)
            print("signed:", signature)
        
            node_profile = self.graph.get_node_profile(source_node_rid)
            
            if node_profile:
                pub_key = PublicKey.from_der(node_profile.public_key)
                
                if not pub_key.verify(signature, resp.content):
                    raise Exception("Invalid signature")
            else:
                raise Exception("Unknown Node RID")            
            
            if target_node_rid != self.identity.rid:
                raise Exception("I am not the target")
            
            timestamp = datetime.fromisoformat(resp.headers.get(KOI_NET_TIMESTAMP))
            if datetime.now(timezone.utc) - timestamp > timedelta(minutes=5):
                raise Exception("Expired message")
            
        if response_model:
            return response_model.model_validate_json(resp.text)
            
    def get_url(self, node_rid: KoiNetNode) -> str:
        """Retrieves URL of a node."""
        
        node_profile = self.graph.get_node_profile(node_rid)
        if not node_profile:
            raise Exception("Node not found")
        if node_profile.node_type != NodeType.FULL:
            raise Exception("Can't query partial node")
        logger.debug(f"Resolved {node_rid!r} to {node_profile.base_url}")
        return node_profile.base_url
    
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