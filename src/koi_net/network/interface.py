import logging
from queue import Queue
from typing import Generic
import httpx
from pydantic import BaseModel
from rid_lib import RID
from rid_lib.core import RIDType
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode

from .graph import NetworkGraph
from .request_handler import RequestHandler
from .response_handler import ResponseHandler
from ..protocol.node import NodeType
from ..protocol.edge import EdgeType
from ..protocol.event import Event
from ..identity import NodeIdentity
from ..config import Config, ConfigType

logger = logging.getLogger(__name__)


class EventQueueModel(BaseModel):
    webhook: dict[KoiNetNode, list[Event]]
    poll: dict[KoiNetNode, list[Event]]

type EventQueue = dict[RID, Queue[Event]]

class NetworkInterface(Generic[ConfigType]):
    """A collection of functions and classes to interact with the KOI network."""
    
    config: ConfigType    
    identity: NodeIdentity
    cache: Cache
    graph: NetworkGraph
    request_handler: RequestHandler
    response_handler: ResponseHandler
    poll_event_queue: EventQueue
    webhook_event_queue: EventQueue
    
    def __init__(
        self, 
        config: ConfigType,
        cache: Cache, 
        identity: NodeIdentity
    ):
        self.config = config
        self.identity = identity
        self.cache = cache
        self.graph = NetworkGraph(cache, identity)
        self.request_handler = RequestHandler(cache, self.graph)
        self.response_handler = ResponseHandler(cache)
        
        self.poll_event_queue = dict()
        self.webhook_event_queue = dict()
        self._load_event_queues()
    
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
        logger.debug(f"Pushing event {event.event_type} {event.rid} to {node}")
            
        node_profile = self.graph.get_node_profile(node)
        if not node_profile:
            logger.warning(f"Node {node!r} unknown to me")
        
        # if there's an edge from me to the target node, override broadcast type
        edge_profile = self.graph.get_edge_profile(
            source=self.identity.rid,
            target=node
        )
        
        if edge_profile:
            if edge_profile.edge_type == EdgeType.WEBHOOK:
                event_queue = self.webhook_event_queue
            elif edge_profile.edge_type == EdgeType.POLL:
                event_queue = self.poll_event_queue
        else:
            if node_profile.node_type == NodeType.FULL:
                event_queue = self.webhook_event_queue
            elif node_profile.node_type == NodeType.PARTIAL:
                event_queue = self.poll_event_queue
        
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
                logger.debug(f"Dequeued {event.event_type} '{event.rid}'")
                events.append(event)
        
        return events
    
    def flush_poll_queue(self, node: KoiNetNode) -> list[Event]:
        """Flushes a node's poll queue, returning list of events."""
        logger.debug(f"Flushing poll queue for {node}")
        return self._flush_queue(self.poll_event_queue, node)
    
    def flush_webhook_queue(self, node: KoiNetNode):
        """Flushes a node's webhook queue, and broadcasts events.
        
        If node profile is unknown, or node type is not `FULL`, this operation will fail silently. If the remote node cannot be reached, all events will be requeued.
        """
        
        logger.debug(f"Flushing webhook queue for {node}")
        
        node_profile = self.graph.get_node_profile(node)
        
        if not node_profile:
            logger.warning(f"{node!r} not found")
            return
        
        if node_profile.node_type != NodeType.FULL:
            logger.warning(f"{node!r} is a partial node!")
            return
        
        events = self._flush_queue(self.webhook_event_queue, node)
        if not events: return
        
        logger.debug(f"Broadcasting {len(events)} events")
        
        try:  
            self.request_handler.broadcast_events(node, events=events)
            return True
        except httpx.ConnectError:
            logger.warning("Broadcast failed, dropping node")
            for event in events:
                self.push_event_to(event, node)
            return False
            
    def get_state_providers(self, rid_type: RIDType) -> list[KoiNetNode]:
        """Returns list of node RIDs which provide state for the specified RID type."""
        
        logger.debug(f"Looking for state providers of '{rid_type}'")
        provider_nodes = []
        for node_rid in self.cache.list_rids(rid_types=[KoiNetNode]):
            node = self.graph.get_node_profile(node_rid)
                        
            if node.node_type == NodeType.FULL and rid_type in node.provides.state:
                logger.debug(f"Found provider '{node_rid}'")
                provider_nodes.append(node_rid)
        
        if not provider_nodes:
            logger.debug("Failed to find providers")
        return provider_nodes
            
    def fetch_remote_bundle(self, rid: RID):
        """Attempts to fetch a bundle by RID from known peer nodes."""
        
        logger.debug(f"Fetching remote bundle '{rid}'")
        remote_bundle = None
        for node_rid in self.get_state_providers(type(rid)):
            payload = self.request_handler.fetch_bundles(
                node=node_rid, rids=[rid])
            
            if payload.bundles:
                remote_bundle = payload.bundles[0]
                logger.debug(f"Got bundle from '{node_rid}'")
                break
        
        if not remote_bundle:
            logger.warning("Failed to fetch remote bundle")
            
        return remote_bundle
    
    def fetch_remote_manifest(self, rid: RID):
        """Attempts to fetch a manifest by RID from known peer nodes."""
        
        logger.debug(f"Fetching remote manifest '{rid}'")
        remote_manifest = None
        for node_rid in self.get_state_providers(type(rid)):
            payload = self.request_handler.fetch_manifests(
                node=node_rid, rids=[rid])
            
            if payload.manifests:
                remote_manifest = payload.manifests[0]
                logger.debug(f"Got bundle from '{node_rid}'")
                break
        
        if not remote_manifest:
            logger.warning("Failed to fetch remote bundle")
            
        return remote_manifest
    
    def poll_neighbors(self) -> list[Event]:
        """Polls all neighboring nodes and returns compiled list of events.
        
        If this node has no neighbors, it will instead attempt to poll the provided first contact URL.
        """
        
        neighbors = self.graph.get_neighbors()
        
        if not neighbors and self.config.koi_net.first_contact:
            logger.debug("No neighbors found, polling first contact")
            try:
                payload = self.request_handler.poll_events(
                    url=self.config.koi_net.first_contact, 
                    rid=self.identity.rid
                )
                if payload.events:
                    logger.debug(f"Received {len(payload.events)} events from '{self.config.koi_net.first_contact}'")
                return payload.events
            except httpx.ConnectError:
                logger.debug(f"Failed to reach first contact '{self.config.koi_net.first_contact}'")
        
        events = []
        for node_rid in neighbors:
            node = self.graph.get_node_profile(node_rid)
            if not node: continue
            if node.node_type != NodeType.FULL: continue
            
            try:
                payload = self.request_handler.poll_events(
                    node=node_rid, 
                    rid=self.identity.rid
                )
                if payload.events:
                    logger.debug(f"Received {len(payload.events)} events from {node_rid!r}")
                events.extend(payload.events)
            except httpx.ConnectError:
                logger.debug(f"Failed to reach node '{node_rid}'")
                continue
            
        return events                
        
        