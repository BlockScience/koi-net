from logging import getLogger
from rid_lib.types import KoiNetNode
from rid_lib import RIDType
from koi_net.context import HandlerContext
from koi_net.protocol.api_models import ErrorResponse
from .protocol.event import Event, EventType


logger = getLogger(__name__)


class Actor:
    """Basic node actions.
    
    Functions defined here used by multiple subsystems.
    """
    
    def __init__(self, ctx: HandlerContext):
        self.ctx = ctx
    
    def handshake_with(self, target: KoiNetNode):
        """Initiates a handshake with target node.
        
        Pushes successive `FORGET` and `NEW` events to target node to
        reset the target's cache in case it already knew this node. 
        """
        
        logger.debug(f"Initiating handshake with {target}")
        self.ctx.event_queue.push_event_to(
            Event.from_rid(
                event_type=EventType.FORGET, 
                rid=self.ctx.identity.rid),
            node=target
        )
            
        self.ctx.event_queue.push_event_to(
            event=Event.from_bundle(
                event_type=EventType.NEW, 
                bundle=self.ctx.cache.read(self.ctx.identity.rid)),
            node=target
        )
        
        self.ctx.event_queue.flush_webhook_queue(target)
        
    def identify_coordinators(self) -> list[KoiNetNode]:
        """Returns node's providing state for `orn:koi-net.node`."""
        return self.ctx.resolver.get_state_providers(KoiNetNode)
        
    def catch_up_with(self, target: KoiNetNode, rid_types: list[RIDType] = []):
        """Fetches and processes knowledge objects from target node.
        
        Args:
            target: Node to catch up with
            rid_types: RID types to fetch from target (all types if list is empty)
        """
        logger.debug(f"catching up with {target} on {rid_types or 'all types'}")
        
        payload = self.ctx.request_handler.fetch_manifests(
            node=target,
            rid_types=rid_types
        )
        if type(payload) == ErrorResponse:
            logger.debug("failed to reach node")
            return
        
        for manifest in payload.manifests:
            if manifest.rid == self.ctx.identity.rid:
                continue
            
            self.ctx.handle(
                manifest=manifest,
                source=target
            )