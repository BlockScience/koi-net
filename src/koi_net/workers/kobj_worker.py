import queue
import traceback
from logging import Logger

from ..config.base import BaseNodeConfig
from ..processor.pipeline import KnowledgePipeline
from ..processor.kobj_queue import KobjQueue
from ..build.threaded_component import ThreadedComponent


class End:
    """Class for STOP_WORKER sentinel pushed to worker queues."""
    pass

STOP_WORKER = End()


class KnowledgeProcessingWorker(ThreadedComponent):
    """Thread worker that processes the `kobj_queue`."""
    
    def __init__(
        self,
        log: Logger,
        config: BaseNodeConfig,
        kobj_queue: KobjQueue,
        pipeline: KnowledgePipeline,
        root_dir
    ):
        self.log = log
        self.config = config
        self.kobj_queue = kobj_queue
        self.pipeline = pipeline
        self.root_dir = root_dir
        
    def stop(self):
        self.kobj_queue.q.put(STOP_WORKER)
        super().stop()
        
    def run(self):
        while True:
            try:
                item = self.kobj_queue.q.get(timeout=self.config.koi_net.kobj_worker.queue_timeout)
                try:
                    if item is STOP_WORKER:
                        self.log.info("Received 'STOP_WORKER' signal, shutting down...")
                        return
                    
                    self.log.info(f"Dequeued {item!r}")
                    
                    self.pipeline.process(item)
                finally:
                    self.kobj_queue.q.task_done()
                    
            except queue.Empty:
                pass
            
            except Exception:
                traceback.print_exc()
                continue
