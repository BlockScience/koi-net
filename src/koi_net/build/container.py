import threading
import structlog

from .artifact import BuildArtifact
from .consts import START_FUNC_NAME, STOP_FUNC_NAME

log = structlog.stdlib.get_logger()


class NodeContainer:
    """Dummy 'shape' for node containers built by assembler."""
    _artifact: BuildArtifact
    
    shutdown_event: threading.Event
    
    def __init__(self, artifact, **kwargs):
        self._artifact = artifact
        
        # adds all components as attributes of this instance
        for name, comp in kwargs.items():
            setattr(self, name, comp)
    
    def run(self):
        try:
            self.start()
            self.shutdown_event.wait()
        except KeyboardInterrupt:
            log.info("Received keyboard interrupt")
            self.shutdown_event.set()
        finally:
            self.stop()
    
    def start(self):
        log.info("Starting node...")
        for comp_name in self._artifact.start_order:
            comp = getattr(self, comp_name)
            start_func = getattr(comp, START_FUNC_NAME)
            log.info(f"Starting {comp_name}...")
            start_func()
            
    def stop(self):
        log.info("Stopping node...")
        for comp_name in self._artifact.stop_order:
            comp = getattr(self, comp_name)
            stop_func = getattr(comp, STOP_FUNC_NAME)
            log.info(f"Stopping {comp_name}...")
            stop_func()
