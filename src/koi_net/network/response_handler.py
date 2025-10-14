import structlog
from rid_lib import RID
from rid_lib.types import KoiNetNode
from rid_lib.ext import Manifest, Cache
from rid_lib.ext.bundle import Bundle

from koi_net.network.poll_event_buffer import PollEventBuffer
from koi_net.processor.kobj_queue import KobjQueue
from koi_net.protocol.consts import BROADCAST_EVENTS_PATH, FETCH_BUNDLES_PATH, FETCH_MANIFESTS_PATH, FETCH_RIDS_PATH, POLL_EVENTS_PATH
from koi_net.protocol.envelope import SignedEnvelope
from koi_net.protocol.model_map import API_MODEL_MAP
from koi_net.secure import Secure

from ..protocol.api_models import (
    ApiModels,
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
    poll_event_buf: PollEventBuffer
    
    def __init__(
        self, 
        cache: Cache,
        kobj_queue: KobjQueue,
        poll_event_buf: PollEventBuffer,
        secure: Secure
    ):
        self.cache = cache
        self.kobj_queue = kobj_queue
        self.poll_event_buf = poll_event_buf
        self.secure = secure
    
    def handle_response(self, path: str, req: SignedEnvelope):
        self.secure.validate_envelope(req)
        
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
        
        return self.secure.create_envelope(
            payload=response,
            target=req.source_node
        )
        
    def broadcast_events_handler(self, req: EventsPayload, source: KoiNetNode):
        log.info(f"Request to broadcast events, received {len(req.events)} event(s)")
        
        for event in req.events:
            self.kobj_queue.put_kobj(event=event, source=source)
        
    def poll_events_handler(
        self, 
        req: PollEvents, 
        source: KoiNetNode
    ) -> EventsPayload:
        log.info(f"Request to poll events")
        events = self.poll_event_buf.flush(source, limit=req.limit)
        return EventsPayload(events=events)
        
    def fetch_rids_handler(
        self, 
        req: FetchRids, 
        source: KoiNetNode
    ) -> RidsPayload:
        """Returns response to fetch RIDs request."""
        log.info(f"Request to fetch rids, allowed types {req.rid_types}")
        rids = self.cache.list_rids(req.rid_types)
        
        return RidsPayload(rids=rids)
        
    def fetch_manifests_handler(self, 
        req: FetchManifests, 
        source: KoiNetNode
    ) -> ManifestsPayload:
        """Returns response to fetch manifests request."""
        log.info(f"Request to fetch manifests, allowed types {req.rid_types}, rids {req.rids}")
        
        manifests: list[Manifest] = []
        not_found: list[RID] = []
        
        for rid in (req.rids or self.cache.list_rids(req.rid_types)):
            bundle = self.cache.read(rid)
            if bundle:
                manifests.append(bundle.manifest)
            else:
                not_found.append(rid)
        
        return ManifestsPayload(manifests=manifests, not_found=not_found)
        
    def fetch_bundles_handler(
        self, 
        req: FetchBundles, 
        source: KoiNetNode
    ) -> BundlesPayload:
        """Returns response to fetch bundles request."""
        log.info(f"Request to fetch bundles, requested rids {req.rids}")
        
        bundles: list[Bundle] = []
        not_found: list[RID] = []

        for rid in req.rids:
            bundle = self.cache.read(rid)
            if bundle:
                bundles.append(bundle)
            else:
                not_found.append(rid)
            
        return BundlesPayload(bundles=bundles, not_found=not_found)