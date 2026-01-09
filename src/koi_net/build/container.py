from pathlib import Path
import threading
from logging import Logger
from typing import Any

from .artifact import BuildArtifact
from .consts import START_FUNC_NAME, STOP_FUNC_NAME
from ..utils import bind_logdir


class NodeContainer:
    """Dummy 'shape' for node containers built by assembler."""
    _artifact: BuildArtifact
    
    shutdown_event: threading.Event
    startup_event: threading.Event
    log: Logger
    root_dir: Path
    
    # TODO: prevent starting twice or stopping when not alive
    # TODO: figure out whether control loop is necessary, new set of primitives for coordinating node lifecycle internally
    
    def __init__(self, artifact, components: dict[str, Any]):
        self._artifact = artifact
        
        # adds all components as attributes of this instance
        for name, comp in components.items():
            setattr(self, name, comp)
    
    @bind_logdir
    def run(self):
        try:
            self.start()
            self.startup_event.set()
            self.shutdown_event.wait()
        except KeyboardInterrupt:
            self.log.info("Received keyboard interrupt")
            self.shutdown_event.set()
        finally:
            self.stop()
    
    @bind_logdir
    def start(self):
        self.log.info("Starting node...")
        for comp_name in self._artifact.start_order:
            comp = getattr(self, comp_name)
            start_func = getattr(comp, START_FUNC_NAME)
            self.log.info(f"Starting {comp_name}...")
            start_func()
    
    @bind_logdir
    def stop(self):
        self.log.info("Stopping node...")
        for comp_name in self._artifact.stop_order:
            comp = getattr(self, comp_name)
            stop_func = getattr(comp, STOP_FUNC_NAME)
            self.log.info(f"Stopping {comp_name}...")
            stop_func()
