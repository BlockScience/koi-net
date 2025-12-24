import threading

from ..build import comp_order


class End:
    """Class for STOP_WORKER sentinel pushed to worker queues."""
    pass

STOP_WORKER = End()

@comp_order.worker
class ThreadWorker:
    """Base class for thread workers."""
    
    thread: threading.Thread
    
    def __init__(self):
        self.thread = threading.Thread(target=self.run)
        
    def start(self):
        self.thread.start()
        
    def stop(self):
        if self.thread.is_alive():
            self.thread.join()
        
    def run(self):
        """Processing loop for thread."""
        pass