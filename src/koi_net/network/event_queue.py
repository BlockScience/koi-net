import logging
from queue import Queue
import httpx
from pydantic import BaseModel
from rid_lib import RID
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode

from .graph import NetworkGraph
from .request_handler import NodeNotFoundError, RequestHandler
from ..protocol.node import NodeProfile, NodeType
from ..protocol.edge import EdgeProfile, EdgeType
from ..protocol.event import Event
from ..identity import NodeIdentity
from ..config import NodeConfig
from ..effector import Effector

logger = logging.getLogger(__name__)


class EventQueueModel(BaseModel):
    webhook: dict[KoiNetNode, list[Event]]
    poll: dict[KoiNetNode, list[Event]]

type EventQueue = dict[RID, Queue[Event]]

class NetworkEventQueue:
    """A collection of functions and classes to interact with the KOI network."""
    
    config: NodeConfig    
    identity: NodeIdentity
    effector: Effector
    cache: Cache
    graph: NetworkGraph
    request_handler: RequestHandler
    poll_event_queue: EventQueue
    webhook_event_queue: EventQueue
    
    def __init__(
        self, 
        config: NodeConfig,
        cache: Cache, 
        identity: NodeIdentity,
        effector: Effector,
        graph: NetworkGraph,
        request_handler: RequestHandler,
    ):
        self.config = config
        self.identity = identity
        self.cache = cache
        self.graph = graph
        self.request_handler = request_handler
        self.effector = effector
        
        self.poll_event_queue = dict()
        self.webhook_event_queue = dict()
    
    def _load_event_queues(self):
        """Loads event queues from storage."""
        try:
            with open(self.config.koi_net.event_queues_path, "r") as f:
                queues = EventQueueModel.model_validate_json(f.read())
            
            for node in queues.poll.keys():
                for event in queues.poll[node]:
                    queue = self.poll_event_queue.setdefault(node, Queue())
                    queue.put(event)
            
            for node in queues.webhook.keys():
                for event in queues.webhook[node]:
                    queue = self.webhook_event_queue.setdefault(node, Queue())
                    queue.put(event)
                                
        except FileNotFoundError:
            return
        
    def _save_event_queues(self):
        """Writes event queues to storage."""
        events_model = EventQueueModel(
            poll={
                node: list(queue.queue) 
                for node, queue in self.poll_event_queue.items()
                if not queue.empty()
            },
            webhook={
                node: list(queue.queue) 
                for node, queue in self.webhook_event_queue.items()
                if not queue.empty()
            }
        )
        
        if len(events_model.poll) == 0 and len(events_model.webhook) == 0:
            return
        
        with open(self.config.koi_net.event_queues_path, "w") as f:
            f.write(events_model.model_dump_json(indent=2))
    
    def push_event_to(self, event: Event, node: KoiNetNode, flush=False):
        """Pushes event to queue of specified node.
        
        Event will be sent to webhook or poll queue depending on the node type and edge type of the specified node. If `flush` is set to `True`, the webhook queued will be flushed after pushing the event.
        """
        logger.debug(f"Pushing event {event.event_type} {event.rid!r} to {node}")
                        
        node_bundle = self.effector.deref(node)
        
        # if there's an edge from me to the target node, override broadcast type
        edge_rid = self.graph.get_edge(
            source=self.identity.rid,
            target=node
        )
        
        edge_bundle = self.effector.deref(edge_rid) if edge_rid else None
        
        if edge_bundle:
            logger.debug(f"Found edge from me to {node!r}")
            edge_profile = edge_bundle.validate_contents(EdgeProfile)
            if edge_profile.edge_type == EdgeType.WEBHOOK:
                event_queue = self.webhook_event_queue
            elif edge_profile.edge_type == EdgeType.POLL:
                event_queue = self.poll_event_queue
                
        elif node_bundle:
            logger.debug(f"Found bundle for {node!r}")
            node_profile = node_bundle.validate_contents(NodeProfile)
            if node_profile.node_type == NodeType.FULL:
                event_queue = self.webhook_event_queue
            elif node_profile.node_type == NodeType.PARTIAL:
                event_queue = self.poll_event_queue
        
        elif node == self.config.koi_net.first_contact.rid:
            logger.debug(f"Node {node!r} is my first contact")
            # first contact node is always a webhook node
            event_queue = self.webhook_event_queue
        
        else:
            logger.warning(f"Node {node!r} unknown to me")
            return
        
        queue = event_queue.setdefault(node, Queue())
        queue.put(event)
                
        if flush and event_queue is self.webhook_event_queue:
            self.flush_webhook_queue(node)
            
    def _flush_queue(self, event_queue: EventQueue, node: KoiNetNode) -> list[Event]:
        """Flushes a node's queue, returning list of events."""
        queue = event_queue.get(node)
        events = list()
        if queue:
            while not queue.empty():
                event = queue.get()
                logger.debug(f"Dequeued {event.event_type} {event.rid!r}")
                events.append(event)
        
        return events
    
    def flush_poll_queue(self, node: KoiNetNode) -> list[Event]:
        """Flushes a node's poll queue, returning list of events."""
        logger.debug(f"Flushing poll queue for {node}")
        return self._flush_queue(self.poll_event_queue, node)
    
    def flush_webhook_queue(self, node: KoiNetNode, requeue_on_fail: bool = True):
        """Flushes a node's webhook queue, and broadcasts events.
        
        If node profile is unknown, or node type is not `FULL`, this operation will fail silently. If the remote node cannot be reached, all events will be requeued.
        """
        
        logger.debug(f"Flushing webhook queue for {node}")
        
        # node_bundle = self.effector.deref(node)
        
        # if not node_bundle:
        #     logger.warning(f"{node!r} not found")
        #     return
        
        # node_profile = node_bundle.validate_contents(NodeProfile)
        
        # if node_profile.node_type != NodeType.FULL:
        #     logger.warning(f"{node!r} is a partial node!")
        #     return
        
        events = self._flush_queue(self.webhook_event_queue, node)
        if not events: return
        
        logger.debug(f"Broadcasting {len(events)} events")
        
        try:  
            self.request_handler.broadcast_events(node, events=events)

        except NodeNotFoundError:
            logger.warning("Broadcast failed (node not found)")
            
        except httpx.ConnectError:
            logger.warning("Broadcast failed (couldn't connect)")
            
            if requeue_on_fail:
                for event in events:
                    self.push_event_to(event, node)