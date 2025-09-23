from logging import getLogger
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode
from rid_lib import RIDType
from koi_net.identity import NodeIdentity
from koi_net.network.event_queue import EventQueue
from koi_net.network.request_handler import RequestHandler
from koi_net.network.resolver import NetworkResolver
from koi_net.processor.kobj_queue import KobjQueue
from koi_net.protocol.api_models import ErrorResponse
from .protocol.event import Event, EventType


logger = getLogger(__name__)



class Behaviors:
    def __init__(self, cache: Cache, identity: NodeIdentity, event_queue: EventQueue, resolver: NetworkResolver, request_handler: RequestHandler, kobj_queue: KobjQueue):
        self.cache = cache
        self.identity = identity
        self.event_queue = event_queue
        self.resolver = resolver
        self.request_handler = request_handler
        self.kobj_queue = kobj_queue

    def handshake_with(self, target: KoiNetNode):
        """Initiates a handshake with target node.
        Pushes successive `FORGET` and `NEW` events to target node to
        reset the target's cache in case it already knew this node. 
        """
        logger.debug(f"Initiating handshake with {target}")
        self.event_queue.push_event_to(
            Event.from_rid(
                event_type=EventType.FORGET, 
                rid=self.identity.rid),
            target=target
        )
        self.event_queue.push_event_to(
            event=Event.from_bundle(
                event_type=EventType.NEW, 
                bundle=self.cache.read(self.identity.rid)),
            target=target
        )
        # self.ctx.event_queue.flush_webhook_queue(target)

    def identify_coordinators(self) -> list[KoiNetNode]:
        """Returns node's providing state for `orn:koi-net.node`."""
        return self.resolver.get_state_providers(KoiNetNode)

    def catch_up_with(self, target: KoiNetNode, rid_types: list[RIDType] = []):
        """Fetches and processes knowledge objects from target node.
        Args:
            target: Node to catch up with
            rid_types: RID types to fetch from target (all types if list is empty)
        """
        logger.debug(f"catching up with {target} on {rid_types or 'all types'}")
        payload = self.request_handler.fetch_manifests(
            node=target,
            rid_types=rid_types
        )
        if type(payload) == ErrorResponse:
            logger.debug("failed to reach node")
            return
        for manifest in payload.manifests:
            if manifest.rid == self.identity.rid:
                continue
            self.kobj_queue.put_kobj(
                manifest=manifest,
                source=target
            )