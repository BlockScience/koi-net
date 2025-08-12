import logging
import httpx
from rid_lib import RID
from rid_lib.types.koi_net_node import KoiNetNode

from ..identity import NodeIdentity
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
    ResponseModels,
    ErrorResponse
)
from ..protocol.envelope import SignedEnvelope
from ..protocol.consts import (
    BROADCAST_EVENTS_PATH,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH
)
from ..protocol.node import NodeProfile, NodeType
from ..secure import Secure
from ..effector import Effector

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .error_handler import ErrorHandler


logger = logging.getLogger(__name__)


# Custom error types for request handling
class SelfRequestError(Exception):
    """Raised when a node tries to request itself."""
    pass

class PartialNodeQueryError(Exception):
    """Raised when attempting to query a partial node."""
    pass

class NodeNotFoundError(Exception):
    """Raised when a node URL cannot be found."""
    pass

class UnknownPathError(Exception):
    """Raised when an unknown path is requested."""
    pass

class RequestHandler:
    """Handles making requests to other KOI nodes."""
    
    effector: Effector
    identity: NodeIdentity
    secure: Secure
    error_handler: "ErrorHandler"
    
    def __init__(
        self, 
        effector: Effector,
        identity: NodeIdentity,
        secure: Secure
    ):
        self.effector = effector
        self.identity = identity
        self.secure = secure
        
    def set_error_handler(self, error_handler: "ErrorHandler"):
        self.error_handler = error_handler
    
    def get_url(self, node_rid: KoiNetNode) -> str:
        """Retrieves URL of a node."""
        
        logger.debug(f"Getting URL for {node_rid!r}")
        node_url = None
        
        if node_rid == self.identity.rid:
            raise SelfRequestError("Don't talk to yourself")
        
        node_bundle = self.effector.deref(node_rid)
                
        if node_bundle:
            node_profile = node_bundle.validate_contents(NodeProfile)
            logger.debug(f"Found node profile: {node_profile}")
            if node_profile.node_type != NodeType.FULL:
                raise PartialNodeQueryError("Can't query partial node")
            node_url = node_profile.base_url
        
        else:
            if node_rid == self.identity.config.koi_net.first_contact.rid:
                logger.debug("Found URL of first contact")
                node_url = self.identity.config.koi_net.first_contact.url
        
        if not node_url:
            raise NodeNotFoundError("Node not found")
        
        logger.debug(f"Resolved {node_rid!r} to {node_url}")
        return node_url
    
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
        
        try:
            result = httpx.post(url, data=signed_envelope.model_dump_json())
        except httpx.ConnectError as err:
            logger.debug("Failed to connect")
            self.error_handler.handle_connection_error(node)
            raise err
        
        if result.status_code != 200:
            resp = ErrorResponse.model_validate_json(result.text)
            self.error_handler.handle_protocol_error(resp.error, node)
            return resp
        
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
            raise UnknownPathError(f"Unknown path '{path}'")
        
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
        if type(resp) != ErrorResponse:
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
        if type(resp) != ErrorResponse:
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
        if type(resp) != ErrorResponse:
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
        if type(resp) != ErrorResponse:
            logger.info(f"Fetched {len(resp.bundles)} bundle(s) from {node!r}")
        return resp