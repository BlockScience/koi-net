import structlog

from ..entrypoints.base import EntryPoint
from .artifact import BuildArtifact
from .consts import START_FUNC_NAME, STOP_FUNC_NAME

log = structlog.stdlib.get_logger()


class NodeContainer:
    """Dummy 'shape' for node containers built by assembler."""
    _artifact: BuildArtifact
    
    entrypoint: EntryPoint
    
    def __init__(self, artifact, **kwargs):
        self._artifact = artifact
        
        # adds all components as attributes of this instance
        for name, comp in kwargs.items():
            setattr(self, name, comp)
    
    def run(self):
        try:
            self.start()
            self.entrypoint.run()
        except KeyboardInterrupt:
            log.info("Keyboard interrupt!")
        finally:
            self.stop()
    
    def start(self):
        log.info("Starting node...")
        for comp_name in self._artifact.start_order:
            comp = getattr(self, comp_name)
            start_func = getattr(comp, START_FUNC_NAME)
            start_func()
            
    def stop(self):
        log.info("Stopping node...")
        for comp_name in self._artifact.stop_order:
            comp = getattr(self, comp_name)
            stop_func = getattr(comp, STOP_FUNC_NAME)
            stop_func()