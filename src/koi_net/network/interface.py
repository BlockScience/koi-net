import logging
from queue import Queue
from pydantic import BaseModel
from rid_lib import RID
from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode
from .graph import NetworkGraph
from .adapter import NetworkAdapter
from ..protocol.node import NodeModel, NodeType
from ..protocol.event import Event

logger = logging.getLogger(__name__)


class EventQueueModel(BaseModel):
    webhook: dict[KoiNetNode, list[Event]]
    poll: dict[KoiNetNode, list[Event]]


class NetworkInterface:
    graph: NetworkGraph
    adapter: NetworkAdapter
    poll_event_queue: dict[RID, Queue]
    webhook_event_queue: dict[RID, Queue]
    
    def __init__(self, file_path, cache: Cache, me: RID):
        self.me = me
        self.cache = cache
        self.adapter = NetworkAdapter(cache)
        self.graph = NetworkGraph(cache, me)
        self.event_queues_file_path = file_path
        
        self.poll_event_queue = dict()
        self.webhook_event_queue = dict()
        self.load_queues()
    
    def load_queues(self):
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
        
    def save_queues(self):
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
                
        with open(self.event_queues_file_path, "w") as f:
            f.write(events_model.model_dump_json(indent=2))
                
    
    def push_event(self, event: Event, flush=False):
        subscribers = self.graph.get_neighbors(
            direction="out", 
            allowed_type=type(event.rid)
        )
        logger.info(f"Pushing event to {len(subscribers)} subscribers")
        for node in subscribers:
            self.push_event_to(event, node, flush)
                
    def push_event_to(self, event: Event, node: RID, flush=False):
        if not isinstance(node, RID):
            raise Exception("node must be of type RID")
        
        logger.info(f"Pushing event {event.event_type} {event.rid} to {node}")
      
        bundle = self.cache.read(node)
        node_profile = NodeModel.model_validate(bundle.contents)
        
        # select queue from node type
        if node_profile.node_type == NodeType.FULL:
            event_queue = self.webhook_event_queue
        elif node_profile.node_type == NodeType.PARTIAL:
            event_queue = self.poll_event_queue
        
        queue = event_queue.setdefault(node, Queue())
        queue.put(event)
                
        if flush and node_profile.node_type == NodeType.FULL:
            self.flush_webhook_queue(node)
    
    def flush_poll_queue(self, node: RID) -> list[Event]:
        logger.info(f"Flushing poll queue for {node}")
        queue = self.poll_event_queue.get(node)
        if not queue: return []
        events = list()

        if queue:
            while not queue.empty():
                events.append(queue.get())
        
        logger.info(f"Returning {len(events)} events")        
        return events
    
    def flush_webhook_queue(self, node: RID):
        logger.info(f"Flushing webhook queue for {node}")
        bundle = self.cache.read(node)
        node_profile = NodeModel.model_validate(bundle.contents)
        
        if node_profile.node_type != NodeType.FULL:
            logger.warning(f"{node} is a partial node!")
            return
        
        queue = self.webhook_event_queue.get(node)
        if not queue: return
        
        events = list()
        while not queue.empty():
            events.append(queue.get())
        
        logger.info(f"Broadcasting {len(events)} events")        
        self.adapter.broadcast_events(node, events=events)
        
        # TODO: retry if request failed
    
    def flush_all_webhook_queues(self):
        for node in self.webhook_event_queue.keys():
            self.flush_webhook_queue(node)
            
    def fetch_remote_bundle(self, rid: RID):
        logger.info(f"Fetching remote bundle '{rid}'")
        remote_bundle = None
        for node_rid in self.cache.list_rids(rid_types=[KoiNetNode]):
            node_bundle = self.cache.read(node_rid)
            node = node_bundle.validate_contents(NodeModel)
            
            if node.node_type == NodeType.FULL and type(rid) in node.provides.state:
                logger.info(f"Attempting to fetch from {node_rid}")
                
                payload = self.adapter.fetch_bundles(
                    node=node_rid, rids=[rid])
                
                if payload.bundles:
                    remote_bundle = payload.bundles[0]
                    logger.info("Got bundle!")
                    break
        
        if not remote_bundle:
            logger.warning("Failed to fetch remote bundle")
            
        return remote_bundle
        