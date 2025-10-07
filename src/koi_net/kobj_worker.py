import queue
import traceback
import structlog

from koi_net.models import END
from koi_net.processor.knowledge_pipeline import KnowledgePipeline
from koi_net.processor.kobj_queue import KobjQueue
from koi_net.worker import ThreadWorker

log = structlog.stdlib.get_logger()


class KnowledgeProcessingWorker(ThreadWorker):
    def __init__(
        self,
        kobj_queue: KobjQueue,
        pipeline: KnowledgePipeline,
        timeout: float = 0.1
    ):
        self.kobj_queue = kobj_queue
        self.pipeline = pipeline
        self.timeout = timeout
        super().__init__()
        
    def run(self):
        log.info("Started kobj worker")
        while True:
            try:
                item = self.kobj_queue.q.get(timeout=self.timeout)
                try:
                    if item is END:
                        log.info("Received 'END' signal, shutting down...")
                        return
                    
                    log.info(f"Dequeued {item!r}")
                    
                    self.pipeline.process(item)
                finally:
                    self.kobj_queue.q.task_done()
                    
            except queue.Empty:
                pass
            
            except Exception as e:
                traceback.print_exc()