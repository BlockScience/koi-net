import structlog

from ..entrypoints.base import EntryPoint
from .artifact import AssemblyArtifact

log = structlog.stdlib.get_logger()


class NodeContainer:
    """Dummy 'shape' for node containers built by assembler."""
    _artifact: AssemblyArtifact
    entrypoint: EntryPoint
    
    def __init__(self, artifact, **kwargs):
        self._artifact = artifact
        
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
            comp.start()
            
    def stop(self):
        log.info("Stopping node...")
        for comp_name in self._artifact.stop_order:
            comp = getattr(self, comp_name)
            comp.stop()