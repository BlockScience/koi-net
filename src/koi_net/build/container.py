import threading
from pathlib import Path
from logging import Logger
from typing import Any

from koi_net.lifecycle import NodeLifecycle, NodeState

from ..logging_context import LoggingContext
from .artifact import BuildArtifact



class NodeContainer:
    """Dummy 'shape' for node containers built by assembler."""
    _artifact: BuildArtifact
    _lifecyle: NodeLifecycle

    # components:
    log: Logger
    logging_context: LoggingContext
    root_dir: Path
    shutdown_signal: threading.Event
    
    def __init__(self, artifact, components: dict[str, Any]):
        self._artifact = artifact
        
        # adds all components as attributes of this instance
        for name, comp in components.items():
            setattr(self, name, comp)
            
        
        self._lifecycle = NodeLifecycle(
            shutdown_signal=self.shutdown_signal,
            log=self.log,
            logging_context=self.logging_context,
            artifact=self._artifact,
            container=self
        )
        
    def start(self, block: bool = True):
        self._lifecycle.start(block=block)
        
    def stop(self, block: bool = True):
        self._lifecycle.stop(block=block)
        
    def get_state(self) -> NodeState:
        return self._lifecycle.state