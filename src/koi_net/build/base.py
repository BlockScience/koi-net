from logging import Logger
from pathlib import Path
import sys
import threading

import structlog

from koi_net.cli.consts import READY_SIGNAL, STOP_SIGNAL
from .assembler import NodeAssembler


class ControlLoop:
    startup_event: threading.Event
    shutdown_event: threading.Event
    
    def __init__(self, startup_event, shutdown_event):
        self.startup_event = startup_event
        self.shutdown_event = shutdown_event
        self.thread = threading.Thread(target=self.run, daemon=True)
        
    def run(self):
        self.startup_event.wait()
        sys.stdout.write("\n" + READY_SIGNAL + "\n")
        sys.stdout.flush()
        
        for line in sys.stdin:
            if line.strip() == STOP_SIGNAL:
                self.shutdown_event.set()
                
        self.shutdown_event.set()
        
    def start(self):
        self.thread.start()

class BaseAssembly(NodeAssembler):
    root_dir: Path
    startup_event: threading.Event = threading.Event
    shutdown_event: threading.Event = threading.Event
    control_loop: ControlLoop = ControlLoop
    log: Logger = lambda root_dir: structlog.stdlib.get_logger().bind(log_dir=root_dir)
    
    def __new__(cls, *args, root_dir: Path, **kwargs):
        cls.root_dir = root_dir
        return super().__new__(cls, *args, **kwargs)
