from logging import Logger
from pathlib import Path
import sys
import threading

import structlog
from structlog.contextvars import bound_contextvars

from .assembler import NodeAssembler

READY_SIGNAL = "READY"
STOP_SIGNAL = "STOP"

class ControlLoop:
    startup_complete: threading.Event
    shutdown_request: threading.Event
    
    def __init__(self, startup_complete, shutdown_request):
        self.startup_complete = startup_complete
        self.shutdown_request = shutdown_request
        
    def run(self):
        self.startup_complete.wait()
        sys.stdout.write("\n" + READY_SIGNAL + "\n")
        sys.stdout.flush()
        
        for line in sys.stdin:
            if line.strip() == STOP_SIGNAL:
                self.shutdown_request.set()
        
        print("CLOSED STDIN")
        
        self.shutdown_request.set()
        
    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

class BaseAssembly(NodeAssembler):
    root_dir: Path
    can_start: threading.Event = threading.Event
    ready: threading.Event = threading.Event
    shutdown_requested: threading.Event = threading.Event
    # control_loop: ControlLoop = ControlLoop
    log: Logger = lambda root_dir: structlog.stdlib.get_logger().bind(log_dir=root_dir)
    
    def __new__(cls, *args, root_dir: Path, **kwargs):
        cls.root_dir = root_dir
        with bound_contextvars(log_dir=root_dir):
            return super().__new__(cls, *args, **kwargs)
