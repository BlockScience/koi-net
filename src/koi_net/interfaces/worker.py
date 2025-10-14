import threading


class End:
    """Class for a sentinel value by knowledge handlers."""
    pass

STOP_WORKER = End()

class ThreadWorker:
    thread: threading.Thread
    
    def __init__(self):
        self.thread = threading.Thread(target=self.run)
        
    def run(self):
        ...