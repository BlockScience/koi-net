import structlog
import httpx
from rid_lib import RID
from rid_lib.ext import Cache
from rid_lib.types.koi_net_node import KoiNetNode

from koi_net.protocol.model_map import API_MODEL_MAP

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
from .error_handler import ErrorHandler

log = structlog.stdlib.get_logger()


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
    
    cache: Cache
    identity: NodeIdentity
    secure: Secure
    error_handler: ErrorHandler
    
    def __init__(
        self, 
        cache: Cache,
        identity: NodeIdentity,
        secure: Secure,
        error_handler: ErrorHandler
    ):
        self.cache = cache
        self.identity = identity
        self.secure = secure
        self.error_handler = error_handler
    
    def get_url(self, node_rid: KoiNetNode) -> str:
        """Retrieves URL of a node from its RID."""
        
        log.debug(f"Getting URL for {node_rid!r}")
        node_url = None
        
        if node_rid == self.identity.rid:
            raise SelfRequestError("Don't talk to yourself")
        
        node_bundle = self.cache.read(node_rid)
                
        if node_bundle:
            node_profile = node_bundle.validate_contents(NodeProfile)
            log.debug(f"Found node profile: {node_profile}")
            if node_profile.node_type != NodeType.FULL:
                raise PartialNodeQueryError("Can't query partial node")
            node_url = node_profile.base_url
        
        else:
            if node_rid == self.identity.config.koi_net.first_contact.rid:
                log.debug("Found URL of first contact")
                node_url = self.identity.config.koi_net.first_contact.url
        
        if not node_url:
            raise NodeNotFoundError("Node not found")
        
        log.debug(f"Resolved {node_rid!r} to {node_url}")
        return node_url
    
    def make_request(
        self,
        node: KoiNetNode,
        path: str, 
        request: RequestModels,
    ) -> ResponseModels | None:
        """Makes a request to a node."""
        url = self.get_url(node) + path
        log.info(f"Making request to {url}")
    
        signed_envelope = self.secure.create_envelope(
            payload=request,
            target=node
        )
        
        try:
            result = httpx.post(
                url, 
                data=signed_envelope.model_dump_json(exclude_none=True)
            )
        except httpx.ConnectError as err:
            log.debug("Failed to connect")
            self.error_handler.handle_connection_error(node)
            raise err
        
        if result.status_code != 200:
            resp = ErrorResponse.model_validate_json(result.text)
            self.error_handler.handle_protocol_error(resp.error, node)
            return resp
        
        resp_env_model = API_MODEL_MAP[path].response_envelope
        if resp_env_model is None:
            return
        
        resp_envelope = resp_env_model.model_validate_json(result.text)
        self.secure.validate_envelope(resp_envelope)
        
        return resp_envelope.payload
    
    def broadcast_events(
        self, 
        node: RID, 
        req: EventsPayload | None = None,
        **kwargs
    ) -> None:
        """Broadcasts events to a node.
        
        Pass `EventsPayload` object, or see `protocol.api_models.EventsPayload` for available kwargs.
        """
        request = req or EventsPayload.model_validate(kwargs)
        self.make_request(node, BROADCAST_EVENTS_PATH, request)
        log.info(f"Broadcasted {len(request.events)} event(s) to {node!r}")
        
    def poll_events(
        self, 
        node: RID, 
        req: PollEvents | None = None,
        **kwargs
    ) -> EventsPayload:
        """Polls events from a node.
        
        Pass `PollEvents` object as `req` or fields as kwargs.
        """
        request = req or PollEvents.model_validate(kwargs)
        resp = self.make_request(node, POLL_EVENTS_PATH, request)
        if type(resp) != ErrorResponse:
            log.info(f"Polled {len(resp.events)} events from {node!r}")
        return resp
        
    def fetch_rids(
        self, 
        node: RID, 
        req: FetchRids | None = None,
        **kwargs
    ) -> RidsPayload:
        """Fetches RIDs from a node.
        
        Pass `FetchRids` object as `req` or fields as kwargs.
        """
        request = req or FetchRids.model_validate(kwargs)
        resp = self.make_request(node, FETCH_RIDS_PATH, request)
        if type(resp) != ErrorResponse:
            log.info(f"Fetched {len(resp.rids)} RID(s) from {node!r}")
        return resp
                
    def fetch_manifests(
        self, 
        node: RID, 
        req: FetchManifests | None = None,
        **kwargs
    ) -> ManifestsPayload:
        """Fetches manifests from a node.
        
        Pass `FetchManifests` object as `req` or fields as kwargs.
        """
        request = req or FetchManifests.model_validate(kwargs)
        resp = self.make_request(node, FETCH_MANIFESTS_PATH, request)
        if type(resp) != ErrorResponse:
            log.info(f"Fetched {len(resp.manifests)} manifest(s) from {node!r}")
        return resp
                
    def fetch_bundles(
        self, 
        node: RID, 
        req: FetchBundles | None = None,
        **kwargs
    ) -> BundlesPayload:
        """Fetches bundles from a node.
        
        Pass `FetchBundles` object as `req` or fields as kwargs.
        """
        request = req or FetchBundles.model_validate(kwargs)
        resp = self.make_request(node, FETCH_BUNDLES_PATH, request)
        if type(resp) != ErrorResponse:
            log.info(f"Fetched {len(resp.bundles)} bundle(s) from {node!r}")
        return resp