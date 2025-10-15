import queue
import traceback
import time
import structlog

from rid_lib.ext import Cache
from rid_lib.types import KoiNetNode

from koi_net.config import NodeConfig
from koi_net.network.event_queue import EventQueue, QueuedEvent
from koi_net.network.request_handler import RequestHandler
from koi_net.network.poll_event_buffer import PollEventBuffer
from koi_net.protocol.event import Event
from koi_net.protocol.node import NodeProfile, NodeType
from koi_net.interfaces.worker import ThreadWorker, STOP_WORKER

log = structlog.stdlib.get_logger()


class EventProcessingWorker(ThreadWorker):
    event_buffer: dict[KoiNetNode, list[Event]]
    buffer_times: dict[KoiNetNode, float]

    def __init__(
        self,
        event_queue: EventQueue,
        request_handler: RequestHandler,
        config: NodeConfig,
        cache: Cache,
        poll_event_buf: PollEventBuffer
    ):
        self.event_queue = event_queue
        self.request_handler = request_handler
        
        self.config = config
        self.cache = cache
        self.poll_event_buf = poll_event_buf
        
        self.timeout: float = 0.1
        self.max_buf_len: int = 5
        self.max_wait_time: float = 1.0
        
        self.event_buffer = dict()
        self.buffer_times = dict()
        
        super().__init__()
        
    def flush_buffer(self, target: KoiNetNode, buffer: list[Event]):
        try:
            self.request_handler.broadcast_events(target, events=buffer)
        except Exception as e:
            traceback.print_exc()
        
        self.event_buffer[target] = []
        self.buffer_times[target] = None
        
    def decide_event(self, item: QueuedEvent) -> bool:
        node_bundle = self.cache.read(item.target)
        if node_bundle: 
            node_profile = node_bundle.validate_contents(NodeProfile)
            
            if node_profile.node_type == NodeType.FULL:
                return True
        
            elif node_profile.node_type == NodeType.PARTIAL:
                self.poll_event_buf.put(item.target, item.event)
                return False
        
        elif item.target == self.config.koi_net.first_contact.rid:
            return True
        
        else:
            log.warning(f"Couldn't handle event {item.event!r} in queue, node {item.target!r} unknown to me")
            return False
        

    def run(self):
        log.info("Started event worker")
        while True:
            now = time.time()
            try:
                item = self.event_queue.q.get(timeout=self.timeout)
                
                try:
                    if item is STOP_WORKER:
                        log.info(f"Received 'STOP_WORKER' signal, flushing buffer...")
                        for target in self.event_buffer.keys():
                            self.flush_buffer(target, self.event_buffer[target])
                        return
                    
                    log.info(f"Dequeued {item.event!r} -> {item.target!r}")
                    
                    if not self.decide_event(item):
                        continue
                    
                    event_buf = self.event_buffer.setdefault(item.target, [])
                    if not event_buf:
                        self.buffer_times[item.target] = now
                    
                    event_buf.append(item.event)

                    # When new events are dequeued, check buffer for max length
                    if len(event_buf) >= self.max_buf_len:
                        self.flush_buffer(item.target, event_buf)
                finally:
                    self.event_queue.q.task_done()

            except queue.Empty:
                # On timeout, check all buffers for max wait time
                for target, event_buf in self.event_buffer.items():
                    if (len(event_buf) == 0) or (self.buffer_times.get(target) is None):
                        continue
                    if (now - self.buffer_times[target]) >= self.max_wait_time: 
                        self.flush_buffer(target, event_buf)
                    
            except Exception as e:
                traceback.print_exc()