import logging
import httpx
from koi_net import identity
from rid_lib import RID
from rid_lib.types.koi_net_node import KoiNetNode

from koi_net.identity import NodeIdentity
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
from ..protocol.envelope import SignedEnvelope
from ..protocol.consts import (
    BROADCAST_EVENTS_PATH,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH,
)
from ..protocol.node import NodeProfile, NodeType
from ..secure import Secure
from ..effector import Effector


logger = logging.getLogger(__name__)


class RequestHandler:
    """Handles making requests to other KOI nodes."""
    
    effector: Effector
    identity: NodeIdentity
    secure: Secure
    
    def __init__(
        self, 
        effector: Effector,
        identity: NodeIdentity,
        secure: Secure
    ):
        self.effector = effector
        self.identity = identity
        self.secure = secure
    
    def get_url(self, node_rid: KoiNetNode) -> str:
        """Retrieves URL of a node."""
        
        print(node_rid)
        
        if node_rid == self.identity.rid:
            raise Exception("Don't talk to yourself")
        
        node_bundle = self.effector.deref(node_rid)
        
        if not node_bundle:
            if node_rid == self.identity.config.koi_net.first_contact_rid:
                return self.identity.config.koi_net.first_contact_url
            raise Exception("Node not found")
        node_profile = node_bundle.validate_contents(NodeProfile)
        if node_profile.node_type != NodeType.FULL:
            raise Exception("Can't query partial node")
        logger.debug(f"Resolved {node_rid!r} to {node_profile.base_url}")
        return node_profile.base_url
    
    def make_request(
        self,
        node: KoiNetNode,
        path: str, 
        request: RequestModels,
    ) -> ResponseModels | None:
        url = self.get_url(node) + path
        logger.info(f"Making request to {url}")
    
        signed_envelope = self.secure.create_envelope(
            payload=request,
            target=node
        )
                
        result = httpx.post(url, data=signed_envelope.model_dump_json())
        
        if path == BROADCAST_EVENTS_PATH:
            return None
        
        elif path == POLL_EVENTS_PATH:
            EnvelopeModel = SignedEnvelope[EventsPayload]
        elif path == FETCH_RIDS_PATH:
            EnvelopeModel = SignedEnvelope[RidsPayload]
        elif path == FETCH_MANIFESTS_PATH:
            EnvelopeModel = SignedEnvelope[ManifestsPayload]
        elif path == FETCH_BUNDLES_PATH:
            EnvelopeModel = SignedEnvelope[BundlesPayload]
        else:
            raise Exception(f"Unknown path '{path}'")
        
        resp_envelope = EnvelopeModel.model_validate_json(result.text)        
        self.secure.validate_envelope(resp_envelope)
        
        return resp_envelope.payload
    
    def broadcast_events(
        self, 
        node: RID, 
        req: EventsPayload | None = None,
        **kwargs
    ) -> None:
        """See protocol.api_models.EventsPayload for available kwargs."""
        request = req or EventsPayload.model_validate(kwargs)
        self.make_request(node, BROADCAST_EVENTS_PATH, request)
        logger.info(f"Broadcasted {len(request.events)} event(s) to {node!r}")
        
    def poll_events(
        self, 
        node: RID, 
        req: PollEvents | None = None,
        **kwargs
    ) -> EventsPayload:
        """See protocol.api_models.PollEvents for available kwargs."""
        request = req or PollEvents.model_validate(kwargs)
        resp = self.make_request(node, POLL_EVENTS_PATH, request)
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
        resp = self.make_request(node, FETCH_RIDS_PATH, request)
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
        resp = self.make_request(node, FETCH_MANIFESTS_PATH, request)
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
        resp = self.make_request(node, FETCH_BUNDLES_PATH, request)
        logger.info(f"Fetched {len(resp.bundles)} bundle(s) from {node!r}")
        return resp