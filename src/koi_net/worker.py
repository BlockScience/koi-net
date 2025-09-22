import threading

class ThreadWorker:
    thread: threading.Thread
    
    def __init__(self):
        self.thread = threading.Thread(target=self.run)
        
    def run(self):
        ...