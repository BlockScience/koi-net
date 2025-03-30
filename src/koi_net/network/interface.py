import logging
from queue import Queue
import httpx
from pydantic import BaseModel
from rid_lib import RID
from rid_lib.core import RIDType
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode

from koi_net.protocol.edge import EdgeProfile, EdgeType
from .graph import NetworkGraph
from .adapter import NetworkAdapter
from ..protocol.node import NodeProfile, NodeType
from ..protocol.event import Event
from ..identity import NodeIdentity

logger = logging.getLogger(__name__)


class EventQueueModel(BaseModel):
    webhook: dict[KoiNetNode, list[Event]]
    poll: dict[KoiNetNode, list[Event]]


class NetworkInterface:
    graph: NetworkGraph
    adapter: NetworkAdapter
    first_contact: str | None
    poll_event_queue: dict[RID, Queue[Event]]
    webhook_event_queue: dict[RID, Queue[Event]]
    
    def __init__(
        self, 
        file_path: str,
        first_contact: str | None,
        cache: Cache, 
        identity: NodeIdentity
    ):
        self.identity = identity
        self.cache = cache
        self.first_contact = first_contact
        self.adapter = NetworkAdapter(cache)
        self.graph = NetworkGraph(cache, identity)
        self.event_queues_file_path = file_path
        
        self.poll_event_queue = dict()
        self.webhook_event_queue = dict()
        self.load_event_queues()
    
    def load_event_queues(self):
        try:
            with open(self.event_queues_file_path, "r") as f:
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
        
    def save_event_queues(self):
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
        
        with open(self.event_queues_file_path, "w") as f:
            f.write(events_model.model_dump_json(indent=2))
                
    def get_node_profile(self, rid: KoiNetNode) -> NodeProfile | None:
        bundle = self.cache.read(rid)
        if bundle:
            return bundle.validate_contents(NodeProfile)
        
    def get_edge_profile(self, source: KoiNetNode, target: KoiNetNode) -> EdgeProfile | None:
        edge_pair = (source, target)
        if edge_pair not in self.graph.dg.edges:
            return
        
        edge_data = self.graph.dg.get_edge_data(*edge_pair)
        if not edge_data: return
        edge_rid = edge_data.get("rid")
        if not edge_rid: return
        
        bundle = self.cache.read(edge_rid)
        if bundle:
            return bundle.validate_contents(EdgeProfile)
    
    def push_event_to(self, event: Event, node: KoiNetNode, flush=False):
        logger.info(f"Pushing event {event.event_type} {event.rid} to {node}")
      
        node_profile = self.get_node_profile(node)
        if not node_profile:
            logger.warning(f"Node {node!r} unknown to me")
        
        # if there's an edge from me to the target node, override broadcast type
        edge_profile = self.get_edge_profile(
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
    
    def flush_poll_queue(self, node: RID) -> list[Event]:
        logger.info(f"Flushing poll queue for {node}")
        queue = self.poll_event_queue.get(node)
        
        events = list()
        if queue:
            while not queue.empty():
                event = queue.get()
                logger.info(f"Dequeued {event.event_type} '{event.rid}' from poll queue")
                events.append(event)
        
        logger.info(f"Returning {len(events)} events")        
        return events
    
    def flush_webhook_queue(self, node: RID):
        logger.info(f"Flushing webhook queue for {node}")
        bundle = self.cache.read(node)
        node_profile = NodeProfile.model_validate(bundle.contents)
        
        if node_profile.node_type != NodeType.FULL:
            logger.warning(f"{node} is a partial node!")
            return
        
        queue = self.webhook_event_queue.get(node)
        if not queue: return
        
        events = list()
        while not queue.empty():
            event = queue.get()
            logger.info(f"Dequeued {event.event_type} '{event.rid}' from webhook queue")
            events.append(event)
        
        logger.info(f"Broadcasting {len(events)} events")
        
        try:  
            self.adapter.broadcast_events(node, events=events)
        except httpx.ConnectError:
            logger.warning("Broadcast failed, requeuing events")
            for event in events:
                queue.put(event)
    
    def flush_all_webhook_queues(self):
        for node in self.webhook_event_queue.keys():
            self.flush_webhook_queue(node)
            
    def get_state_providers(self, rid_type: RIDType):
        logger.info(f"Looking for state providers of '{rid_type}'")
        provider_nodes = []
        for node_rid in self.cache.list_rids(rid_types=[KoiNetNode]):
            node = self.get_node_profile(node_rid)
                        
            if node.node_type == NodeType.FULL and rid_type in node.provides.state:
                logger.info(f"Found provider '{node_rid}'")
                provider_nodes.append(node_rid)
        
        if not provider_nodes:
            logger.info("Failed to find providers")
        return provider_nodes
            
    def fetch_remote_bundle(self, rid: RID):
        logger.info(f"Fetching remote bundle '{rid}'")
        remote_bundle = None
        for node_rid in self.get_state_providers(type(rid)):
            payload = self.adapter.fetch_bundles(
                node=node_rid, rids=[rid])
            
            if payload.manifests:
                remote_bundle = payload.manifests[0]
                logger.info(f"Got bundle from '{node_rid}'")
                break
        
        if not remote_bundle:
            logger.warning("Failed to fetch remote bundle")
            
        return remote_bundle
    
    def fetch_remote_manifest(self, rid: RID):
        logger.info(f"Fetching remote manifest '{rid}'")
        remote_manifest = None
        for node_rid in self.get_state_providers(type(rid)):
            payload = self.adapter.fetch_manifests(
                node=node_rid, rids=[rid])
            
            if payload.manifests:
                remote_manifest = payload.manifests[0]
                logger.info(f"Got bundle from '{node_rid}'")
                break
        
        if not remote_manifest:
            logger.warning("Failed to fetch remote bundle")
            
        return remote_manifest
    
    def poll_neighbors(self) -> list[Event]:
        neighbors = self.graph.get_neighbors()
        
        if not neighbors:
            logger.info("No neighbors found, polling first contact")
            try:
                payload = self.adapter.poll_events(
                    url=self.first_contact, 
                    rid=self.identity.rid
                )
                if payload.events:
                    logger.info(f"Received {len(payload.events)} events from '{self.first_contact}'")
                return payload.events
            except httpx.ConnectError:
                logger.info(f"Failed to reach first contact '{self.first_contact}'")
        
        events = []
        for node_rid in neighbors:
            node = self.get_node_profile(node_rid)
            if not node: continue
            if node.node_type != NodeType.FULL: continue
            
            try:
                payload = self.adapter.poll_events(
                    node=node_rid, 
                    rid=self.identity.rid
                )
                if payload.events:
                    logger.info(f"Received {len(payload.events)} events from {node_rid!r}")
                events.extend(payload.events)
            except httpx.ConnectError:
                logger.info(f"Failed to reach node '{node_rid}'")
                continue
            
        return events                
        
        