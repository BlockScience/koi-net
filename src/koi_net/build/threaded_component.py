import threading
from pathlib import Path

from ..utils import bind_logdir


class ThreadedComponent:
    """Base class for threaded component. Derived classes MUST set `self.root_dir`."""
    
    thread: threading.Thread | None = None
    root_dir: Path
    
    def start(self):
        if self.thread and self.thread.is_alive():
            print("component has already started")
            return
            
        self.thread = threading.Thread(target=self.run_with_log_ctx)
        self.thread.start()
        
    def stop(self):
        if self.thread and self.thread.is_alive():
            self.thread.join()
        else:
            print("component has already stopped")
    
    @bind_logdir
    def run_with_log_ctx(self):
        self.run()
    
    def run(self):
        """Processing loop for thread."""
        pass