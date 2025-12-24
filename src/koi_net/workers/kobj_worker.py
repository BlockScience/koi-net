import queue
import traceback
import structlog

from ..config.base import BaseNodeConfig
from ..processor.pipeline import KnowledgePipeline
from ..processor.kobj_queue import KobjQueue
from .base import ThreadWorker, STOP_WORKER

log = structlog.stdlib.get_logger()


class KnowledgeProcessingWorker(ThreadWorker):
    """Thread worker that processes the `kobj_queue`."""
    
    def __init__(
        self,
        config: BaseNodeConfig,
        kobj_queue: KobjQueue,
        pipeline: KnowledgePipeline
    ):
        self.config = config
        self.kobj_queue = kobj_queue
        self.pipeline = pipeline

        super().__init__()
        
    def stop(self):
        self.kobj_queue.q.put(STOP_WORKER)
        super().stop()
        
    def run(self):
        while True:
            try:
                item = self.kobj_queue.q.get(timeout=self.config.koi_net.kobj_worker.queue_timeout)
                try:
                    if item is STOP_WORKER:
                        log.info("Received 'STOP_WORKER' signal, shutting down...")
                        return
                    
                    log.info(f"Dequeued {item!r}")
                    
                    self.pipeline.process(item)
                finally:
                    self.kobj_queue.q.task_done()
                    
            except queue.Empty:
                pass
            
            except Exception:
                traceback.print_exc()
                continue
