from rid_lib import RID
from rid_lib.ext import Cache, Event, Bundle
from koi_net import EventQueueModel, NodeType
from queue import Queue
from .state import NetworkState
from .adapter import NetworkAdapter


class NetworkInterface:
    def __init__(self, file_path, cache: Cache, me: RID):
        print('CREATED A NEW NETWORK INTERFACE')
        self.state = NetworkState(cache, me)
        self.adapter = NetworkAdapter(self.state)
        self.me = me
        self.event_queues_file_path = file_path
        
        self.poll_event_queue: dict[RID, Queue] = dict()
        self.webhook_event_queue: dict[RID, Queue] = dict()
        self.load_queues()
    
    def load_queues(self):
        print("LOADED QUEUES")
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
                    
            print(self.poll_event_queue)
            
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
        subs = self.state.get_sub_rids(event.rid.context)
        for sub in subs:
            self.push_event_to(event, sub, flush)
                
    def push_event_to(self, event: Event, node: RID, flush=False):
        if not isinstance(node, RID):
            raise Exception("node must be of type RID")
        print(repr(node))
        print("pushing event", event.event_type, event.rid, "to", node)
        node_profile = self.state.get_node(node)
        if not node_profile:
            raise Exception("unknown node", node)
        
        # select queue from node type
        if node_profile.node_type == NodeType.FULL:
            event_queue = self.webhook_event_queue
        elif node_profile.node_type == NodeType.PARTIAL:
            event_queue = self.poll_event_queue
        
        queue = event_queue.setdefault(node, Queue())
        print(queue)
        queue.put(event)
        
        print("queue size:", queue.qsize(), node_profile.node_type)
        
        if flush:
            self.flush_webhook_queue(node)
    
    def flush_poll_queue(self, node: RID) -> list[Event]:
        queue = self.poll_event_queue.get(node)
        if not queue: return []
        print(queue)
        print("flushing poll queue, size:", queue.qsize())
        events = list()
        if queue:
            while not queue.empty():
                events.append(queue.get())
        
        print("got", len(events), "items")
        
        return events
    
    def flush_webhook_queue(self, node: RID):
        node_profile = self.state.get_node(node)
        if not node_profile:
            raise Exception("unknown node", node)
        
        if node_profile.node_type != NodeType.FULL:
            return
            # raise Exception("poll node", node)
        
        queue = self.webhook_event_queue.get(node)
        if not queue: return
        
        events = list()
        while not queue.empty():
            events.append(queue.get())
        
        self.adapter.broadcast_events(node, events=events)
        
        # TODO: retry if request failed
    
    def flush_all_webhook_queues(self):
        for node in self.webhook_event_queue.keys():
            self.flush_webhook_queue(node)
        