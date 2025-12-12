import structlog
from rid_lib import RID
from rid_lib.types import KoiNetNode
from rid_lib.ext import Manifest, Cache
from rid_lib.ext.bundle import Bundle

from ..processor.kobj_queue import KobjQueue
from ..protocol.consts import BROADCAST_EVENTS_PATH, FETCH_BUNDLES_PATH, FETCH_MANIFESTS_PATH, FETCH_RIDS_PATH, POLL_EVENTS_PATH
from ..protocol.envelope import SignedEnvelope
from ..secure_manager import SecureManager
from .event_buffer import EventBuffer


from ..protocol.api_models import (
    EventsPayload,
    PollEvents,
    RidsPayload,
    ManifestsPayload,
    BundlesPayload,
    FetchRids,
    FetchManifests,
    FetchBundles,
)

log = structlog.stdlib.get_logger()


class ResponseHandler:
    """Handles generating responses to requests from other KOI nodes."""
    
    cache: Cache
    kobj_queue: KobjQueue
    poll_event_buf: EventBuffer
    
    def __init__(
        self, 
        cache: Cache,
        kobj_queue: KobjQueue,
        poll_event_buf: EventBuffer,
        secure_manager: SecureManager
    ):
        self.cache = cache
        self.kobj_queue = kobj_queue
        self.poll_event_buf = poll_event_buf
        self.secure_manager = secure_manager
    
    def handle_response(self, path: str, req: SignedEnvelope):
        self.secure_manager.validate_envelope(req)
        
        response_map = {
            BROADCAST_EVENTS_PATH: self.broadcast_events_handler,
            POLL_EVENTS_PATH: self.poll_events_handler,
            FETCH_RIDS_PATH: self.fetch_rids_handler,
            FETCH_MANIFESTS_PATH: self.fetch_manifests_handler,
            FETCH_BUNDLES_PATH: self.fetch_bundles_handler
        }
        
        response = response_map[path](req.payload, req.source_node)
        
        if response is None:
            return
        
        return self.secure_manager.create_envelope(
            payload=response,
            target=req.source_node
        )
        
    def broadcast_events_handler(self, req: EventsPayload, source: KoiNetNode):
        log.info(f"Request to broadcast events, received {len(req.events)} event(s)")
        
        for event in req.events:
            self.kobj_queue.push(event=event, source=source)
        
    def poll_events_handler(
        self, 
        req: PollEvents, 
        source: KoiNetNode
    ) -> EventsPayload:
        events = self.poll_event_buf.flush(source, limit=req.limit)
        log.info(f"Request to poll events, returning {len(events)} event(s)")
        return EventsPayload(events=events)
        
    def fetch_rids_handler(
        self, 
        req: FetchRids, 
        source: KoiNetNode
    ) -> RidsPayload:
        """Returns response to fetch RIDs request."""
        rids = self.cache.list_rids(req.rid_types)
        log.info(f"Request to fetch rids, allowed types {req.rid_types}, returning {len(rids)} RID(s)")
        return RidsPayload(rids=rids)
        
    def fetch_manifests_handler(
        self, 
        req: FetchManifests, 
        source: KoiNetNode
    ) -> ManifestsPayload:
        """Returns response to fetch manifests request."""        
        manifests: list[Manifest] = []
        not_found: list[RID] = []
        
        for rid in (req.rids or self.cache.list_rids(req.rid_types)):
            bundle = self.cache.read(rid)
            if bundle:
                manifests.append(bundle.manifest)
            else:
                not_found.append(rid)
        
        log.info(f"Request to fetch manifests, allowed types {req.rid_types}, rids {req.rids}, returning {len(manifests)} manifest(s)")
        return ManifestsPayload(manifests=manifests, not_found=not_found)
        
    def fetch_bundles_handler(
        self, 
        req: FetchBundles, 
        source: KoiNetNode
    ) -> BundlesPayload:
        """Returns response to fetch bundles request."""
        
        bundles: list[Bundle] = []
        not_found: list[RID] = []

        for rid in req.rids:
            bundle = self.cache.read(rid)
            if bundle:
                bundles.append(bundle)
            else:
                not_found.append(rid)
                
        log.info(f"Request to fetch bundles, requested rids {req.rids}, returning {len(bundles)} bundle(s)")
        return BundlesPayload(bundles=bundles, not_found=not_found)