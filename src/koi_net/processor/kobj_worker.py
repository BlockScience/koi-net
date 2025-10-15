import queue
import traceback
import structlog

from .pipeline import KnowledgePipeline
from .kobj_queue import KobjQueue
from koi_net.interfaces.worker import ThreadWorker, STOP_WORKER

log = structlog.stdlib.get_logger()


class KnowledgeProcessingWorker(ThreadWorker):
    def __init__(
        self,
        kobj_queue: KobjQueue,
        pipeline: KnowledgePipeline
    ):
        self.kobj_queue = kobj_queue
        self.pipeline = pipeline
        self.timeout: float = 0.1

        super().__init__()
        
    def run(self):
        log.info("Started kobj worker")
        while True:
            try:
                item = self.kobj_queue.q.get(timeout=self.timeout)
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
            
            except Exception as e:
                traceback.print_exc()