import sys
import threading
from koi_net.build.assembler import NodeAssembler


class ControlLoop:
    shutdown_event: threading.Event
    
    def __init__(self, shutdown_event):
        self.shutdown_event = shutdown_event
        self.thread = threading.Thread(target=self.run, daemon=True)
        
    def run(self):
        for line in sys.stdin:
            if line.strip() == "STOP":
                self.shutdown_event.set()
                
        self.shutdown_event.set()
        
    def start(self):
        self.thread.start()

class BaseAssembly(NodeAssembler):
    shutdown_event: threading.Event = threading.Event
    control_loop: ControlLoop = ControlLoop