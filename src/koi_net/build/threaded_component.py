import threading
from logging import Logger

from ..logging_context import LoggingContext


class ThreadedComponent:
    """Base class for threaded component. Derived classes MUST set `self.root_dir`."""
    
    thread: threading.Thread | None = None
    
    def __init__(self, log: Logger, logging_context: LoggingContext):
        self.log = log
        self.logging_context = logging_context
    
    def start(self):
        if self.thread and self.thread.is_alive():
            self.log.debug(f"Component {self.__class__.__name__} has already started")
            return
            
        self.thread = threading.Thread(target=self.run_with_log_ctx)
        self.thread.start()
        
    def stop(self):
        if self.thread and self.thread.is_alive():
            self.thread.join()
        else:
            self.log.debug(f"Component {self.__class__.__name__} has already stopped")
    
    def run_with_log_ctx(self):
        with self.logging_context.bound_vars():
            self.run()
    
    def run(self):
        """Processing loop for thread."""
        pass