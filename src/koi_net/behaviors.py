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


def handshake_with(
    cache: Cache,
    identity: NodeIdentity,
    event_queue: EventQueue,
    target: KoiNetNode
):
    """Initiates a handshake with target node.
    
    Pushes successive `FORGET` and `NEW` events to target node to
    reset the target's cache in case it already knew this node. 
    """
    
    logger.debug(f"Initiating handshake with {target}")
    event_queue.push_event_to(
        Event.from_rid(
            event_type=EventType.FORGET, 
            rid=identity.rid),
        target=target
    )
        
    event_queue.push_event_to(
        event=Event.from_bundle(
            event_type=EventType.NEW, 
            bundle=cache.read(identity.rid)),
        target=target
    )
    
    # self.ctx.event_queue.flush_webhook_queue(target)

def identify_coordinators(resolver: NetworkResolver) -> list[KoiNetNode]:
    """Returns node's providing state for `orn:koi-net.node`."""
    return resolver.get_state_providers(KoiNetNode)

def catch_up_with(
    request_handler: RequestHandler,
    identity: NodeIdentity,
    kobj_queue: KobjQueue,
    target: KoiNetNode, 
    rid_types: list[RIDType] = []
):
    """Fetches and processes knowledge objects from target node.
    
    Args:
        target: Node to catch up with
        rid_types: RID types to fetch from target (all types if list is empty)
    """
    logger.debug(f"catching up with {target} on {rid_types or 'all types'}")
    
    payload = request_handler.fetch_manifests(
        node=target,
        rid_types=rid_types
    )
    if type(payload) == ErrorResponse:
        logger.debug("failed to reach node")
        return
    
    for manifest in payload.manifests:
        if manifest.rid == identity.rid:
            continue
        
        kobj_queue.put_kobj(
            manifest=manifest,
            source=target
        )