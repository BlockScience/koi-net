import structlog
import httpx
from rid_lib import RID
from rid_lib.ext import Cache
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
from ..protocol.consts import (
    BROADCAST_EVENTS_PATH,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH
)
from ..protocol.node import NodeProfile, NodeType
from ..protocol.model_map import API_MODEL_MAP
from ..secure_manager import SecureManager
from .error_handler import ErrorHandler

log = structlog.stdlib.get_logger()


class RequestHandler:
    """Handles making requests to other KOI nodes."""
    
    cache: Cache
    identity: NodeIdentity
    secure_manager: SecureManager
    error_handler: ErrorHandler
    
    def __init__(
        self, 
        cache: Cache,
        identity: NodeIdentity,
        secure_manager: SecureManager,
        error_handler: ErrorHandler
    ):
        self.cache = cache
        self.identity = identity
        self.secure_manager = secure_manager
        self.error_handler = error_handler
    
    def get_base_url(self, node_rid: KoiNetNode) -> str:
        """Retrieves URL of a node from its RID."""
        
        node_bundle = self.cache.read(node_rid)
        if node_bundle:
            node_profile = node_bundle.validate_contents(NodeProfile)
            if node_profile.node_type != NodeType.FULL:
                raise PartialNodeQueryError("Partial nodes don't have URLs")
            node_url = node_profile.base_url
        
        elif node_rid == self.identity.config.koi_net.first_contact.rid:
            node_url = self.identity.config.koi_net.first_contact.url
        
        else:
            raise NodeNotFoundError(f"URL not found for {node_rid!r}")
        
        log.debug(f"Resolved {node_rid!r} to {node_url}")
        return node_url
    
    def make_request(
        self,
        node: KoiNetNode,
        path: str, 
        request: RequestModels,
    ) -> ResponseModels | None:
        """Makes a request to a node."""
        if node == self.identity.rid:
            raise SelfRequestError("Don't talk to yourself")
        
        url = self.get_base_url(node) + path
        log.info(f"Making request to {url}")
    
        signed_envelope = self.secure_manager.create_envelope(
            payload=request,
            target=node
        )
        
        data = signed_envelope.model_dump_json(exclude_none=True)
        
        try:
            result = httpx.post(url, data=data)
            self.error_handler.reset_timeout_counter(node)
            
        except httpx.RequestError as err:
            log.debug("Failed to connect")
            self.error_handler.handle_connection_error(node)
            raise err
        
        if result.status_code != 200:
            resp = ErrorResponse.model_validate_json(result.text)
            self.error_handler.handle_protocol_error(resp.error, node)
            return resp
        
        resp_env_model = API_MODEL_MAP[path].response_envelope
        if not resp_env_model: 
            return
        
        resp_envelope = resp_env_model.model_validate_json(result.text)
        self.secure_manager.validate_envelope(resp_envelope)
        
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
    ) -> EventsPayload | ErrorResponse:
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
    ) -> RidsPayload | ErrorResponse:
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
    ) -> ManifestsPayload | ErrorResponse:
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
    ) -> BundlesPayload | ErrorResponse:
        """Fetches bundles from a node.
        
        Pass `FetchBundles` object as `req` or fields as kwargs.
        """
        request = req or FetchBundles.model_validate(kwargs)
        resp = self.make_request(node, FETCH_BUNDLES_PATH, request)
        if type(resp) != ErrorResponse:
            log.info(f"Fetched {len(resp.bundles)} bundle(s) from {node!r}")
        return resp