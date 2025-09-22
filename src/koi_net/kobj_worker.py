import queue
import traceback
import logging

from koi_net.models import END
from koi_net.processor.knowledge_pipeline import KnowledgePipeline
from koi_net.processor.kobj_queue import KobjQueue
from koi_net.worker import ThreadWorker

logger = logging.getLogger(__name__)


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
        logger.info("Started kobj worker")
        while True:
            try:
                item = self.kobj_queue.q.get(timeout=self.timeout)
                try:
                    if item is END:
                        logger.info("Received 'END' signal, shutting down...")
                        return
                    
                    logger.info(f"Dequeued {item!r}")
                    
                    self.pipeline.process(item)
                finally:
                    self.kobj_queue.q.task_done()
                    
            except queue.Empty:
                pass
            
            except Exception as e:
                traceback.print_exc()