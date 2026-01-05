import sys
import threading

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
        sys.stdout.write("READY\n")
        sys.stdout.flush()
        
        for line in sys.stdin:
            if line.strip() == "STOP":
                self.shutdown_event.set()
                
        self.shutdown_event.set()
        
    def start(self):
        self.thread.start()

class BaseAssembly(NodeAssembler):
    startup_event: threading.Event = threading.Event
    shutdown_event: threading.Event = threading.Event
    control_loop: ControlLoop = ControlLoop