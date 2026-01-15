import threading
from enum import StrEnum
from pathlib import Path
from logging import Logger
from typing import Any

from .artifact import BuildArtifact
from .consts import START_FUNC_NAME, STOP_FUNC_NAME
from ..utils import bind_logdir


class NodeState(StrEnum):
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"

class NodeContainer:
    """Dummy 'shape' for node containers built by assembler."""
    _artifact: BuildArtifact
    
    can_start: threading.Event
    ready: threading.Event
    shutdown_requested: threading.Event
    
    log: Logger
    root_dir: Path
    
    def __init__(self, artifact, components: dict[str, Any]):
        self._artifact = artifact
        
        # adds all components as attributes of this instance
        for name, comp in components.items():
            setattr(self, name, comp)
            
        self.can_start.set()
    
    def get_state(self) -> NodeState:
        if self.can_start.is_set():
            return NodeState.IDLE
        else:
            if self.ready.is_set():
                if self.shutdown_requested.is_set():
                    return NodeState.STOPPING
                else:
                    return NodeState.RUNNING
            else:
                return NodeState.STOPPING
    
    @bind_logdir
    def run(self):
        try:
            self.start()
            while not self.shutdown_requested.wait(0.5):
                pass
            
        except KeyboardInterrupt:
            self.log.info("Received keyboard interrupt")
            self.shutdown_requested.set()
            
        finally:
            self.stop()
    
    @bind_logdir
    def start(self):
        if not self.can_start.is_set():
            self.log.warning("Node cannot be started")
            return
        
        self.log.info("Starting node...")
        self.can_start.clear()
        
        try:
            for comp_name in self._artifact.start_order:
                comp = getattr(self, comp_name)
                start_func = getattr(comp, START_FUNC_NAME)
                self.log.info(f"Starting {comp_name}...")
                start_func()
        
        finally:
            self.ready.set()
        
    @bind_logdir
    def stop(self, force: bool = False):
        if not force and not self.ready.is_set() and not self.shutdown_requested.is_set():
            self.log.warning("Node cannot be stopped")
            return
        
        self.ready.clear()
        self.log.info("Stopping node...")
        for comp_name in self._artifact.stop_order:
            comp = getattr(self, comp_name)
            stop_func = getattr(comp, STOP_FUNC_NAME)
            self.log.info(f"Stopping {comp_name}...")
            stop_func()
            
        self.shutdown_requested.clear()
        self.can_start.set()
