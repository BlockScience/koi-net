from queue import Queue
import threading
from dataclasses import dataclass, field
from logging import Logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..logging_context import LoggingContext


@dataclass
class ThreadedComponent:
    """Base class for threaded component. Derived classes MUST set `self.root_dir`."""
    
    log: Logger
    logging_context: "LoggingContext"
    shutdown_signal: threading.Event
    exception_queue: Queue[Exception]
    
    thread: threading.Thread | None = field(init=False, default=None)
    
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
        with self.logging_context.bound_vars(thread=self.__class__.__name__):
            try:
                self.run()
            except Exception as exc:
                self.log.error(str(exc))
                self.log.error("Raising shutdown signal")
                self.shutdown_signal.set()
                self.exception_queue.put(exc)
    
    def run(self):
        """Processing loop for thread."""
        pass