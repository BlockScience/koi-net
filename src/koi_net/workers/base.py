import threading


class End:
    """Class for STOP_WORKER sentinel pushed to worker queues."""
    pass

STOP_WORKER = End()

class ThreadWorker:
    """Base class for thread workers."""
    
    thread: threading.Thread
    
    def __init__(self):
        self.thread = threading.Thread(target=self.run)
        
    def run(self):
        """Processing loop for thread."""
        pass