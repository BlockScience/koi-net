import logging
import queue
import threading
from rid_lib.core import RID
from rid_lib.ext import Bundle, Manifest
from rid_lib.types import KoiNetNode
from ..protocol.event import Event, EventType
from .knowledge_object import KnowledgeObject
from .knowledge_pipeline import KnowledgePipeline


logger = logging.getLogger(__name__)


class ProcessorInterface:
    """Provides access to this node's knowledge processing pipeline."""
    pipeline: KnowledgePipeline
    kobj_queue: queue.Queue[KnowledgeObject]
    use_kobj_processor_thread: bool
    worker_thread: threading.Thread | None = None
    
    def __init__(
        self,
        pipeline: KnowledgePipeline,
        use_kobj_processor_thread: bool,
    ):
        self.pipeline = pipeline
        self.use_kobj_processor_thread = use_kobj_processor_thread
        self.kobj_queue = queue.Queue()
        
        if self.use_kobj_processor_thread:
            self.worker_thread = threading.Thread(
                target=self.kobj_processor_worker,
                daemon=True
            )
    
    def flush_kobj_queue(self):
        """Flushes all knowledge objects from queue and processes them.
        
        NOTE: ONLY CALL THIS METHOD IN SINGLE THREADED NODES, OTHERWISE THIS WILL CAUSE RACE CONDITIONS.
        """
        if self.use_kobj_processor_thread:
            logger.warning("You are using a worker thread, calling this method can cause race conditions!")
        
        while not self.kobj_queue.empty():
            kobj = self.kobj_queue.get()
            logger.debug(f"Dequeued {kobj!r}")
            
            try:
                self.pipeline.process(kobj)
            finally:
                self.kobj_queue.task_done()
            logger.debug("Done")
    
    def kobj_processor_worker(self, timeout=0.1):
        while True:
            try:
                kobj = self.kobj_queue.get(timeout=timeout)
                logger.debug(f"Dequeued {kobj!r}")
                
                try:
                    self.pipeline.process(kobj)
                finally:
                    self.kobj_queue.task_done()
                logger.debug("Done")
            
            except queue.Empty:
                pass
            
            except Exception as e:
                logger.warning(f"Error processing kobj: {e}")
        
    def handle(
        self,
        rid: RID | None = None,
        manifest: Manifest | None = None,
        bundle: Bundle | None = None,
        event: Event | None = None,
        kobj: KnowledgeObject | None = None,
        event_type: EventType | None = None,
        source: KoiNetNode | None = None
    ):
        """Queues provided knowledge to be handled by processing pipeline.
        
        Knowledge may take the form of an RID, manifest, bundle, event, or knowledge object (with an optional event type for RID, manifest, or bundle objects). All objects will be normalized into knowledge objects and queued. If `flush` is `True`, the queue will be flushed immediately after adding the new knowledge.
        """
        if rid:
            _kobj = KnowledgeObject.from_rid(rid, event_type, source)
        elif manifest:
            _kobj = KnowledgeObject.from_manifest(manifest, event_type, source)
        elif bundle:
            _kobj = KnowledgeObject.from_bundle(bundle, event_type, source)
        elif event:
            _kobj = KnowledgeObject.from_event(event, source)
        elif kobj:
            _kobj = kobj
        else:
            raise ValueError("One of 'rid', 'manifest', 'bundle', 'event', or 'kobj' must be provided")
        
        self.kobj_queue.put(_kobj)
        logger.debug(f"Queued {_kobj!r}")
