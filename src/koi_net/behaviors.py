import structlog
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode
from rid_lib import RIDType
from koi_net.identity import NodeIdentity
from koi_net.network.event_queue import EventQueue
from koi_net.network.request_handler import RequestHandler
from koi_net.network.resolver import NetworkResolver
from koi_net.processor.kobj_queue import KobjQueue
from koi_net.protocol.api_models import ErrorResponse

log = structlog.stdlib.get_logger()


class Behaviors:
    def __init__(self, cache: Cache, identity: NodeIdentity, event_queue: EventQueue, resolver: NetworkResolver, request_handler: RequestHandler, kobj_queue: KobjQueue):
        self.cache = cache
        self.identity = identity
        self.event_queue = event_queue
        self.resolver = resolver
        self.request_handler = request_handler
        self.kobj_queue = kobj_queue

    def identify_coordinators(self) -> list[KoiNetNode]:
        """Returns node's providing state for `orn:koi-net.node`."""
        return self.resolver.get_state_providers(KoiNetNode)

    def catch_up_with(self, target: KoiNetNode, rid_types: list[RIDType] = []):
        """Fetches and processes knowledge objects from target node.
        Args:
            target: Node to catch up with
            rid_types: RID types to fetch from target (all types if list is empty)
        """
        log.debug(f"catching up with {target} on {rid_types or 'all types'}")
        payload = self.request_handler.fetch_manifests(
            node=target,
            rid_types=rid_types
        )
        if type(payload) == ErrorResponse:
            log.debug("failed to reach node")
            return
        for manifest in payload.manifests:
            if manifest.rid == self.identity.rid:
                continue
            self.kobj_queue.put_kobj(
                manifest=manifest,
                source=target
            )