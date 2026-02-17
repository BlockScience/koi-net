import threading
from dataclasses import dataclass, field
from queue import Empty, Queue
from logging import Logger
from enum import StrEnum
from typing import Any

from koi_net.build.artifact import BuildArtifact
from koi_net.logging_context import LoggingContext

from .build.component import START_FUNC_NAME, STOP_FUNC_NAME


class NodeState(StrEnum):
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"

@dataclass
class NodeLifecycle:
    
    # injected components:
    log: Logger
    shutdown_signal: threading.Event
    exception_queue: Queue[Exception]
    logging_context: LoggingContext
    artifact: BuildArtifact
    container: Any
    
    # internal vars:
    err: Exception = field(init=False, default=None)
    state: NodeState = field(init=False, default=NodeState.IDLE)
    thread: threading.Thread | None = field(init=False, default=None)
    startup_signal: threading.Event = field(init=False, default_factory=threading.Event)
    
    def start(self, block: bool = True):
        if self.state != NodeState.IDLE:
            self.log.warning("Node can't be started from non-idle state")
            return
        
        self.startup_signal.clear()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        
        if block:
            self.startup_signal.wait()
        
    def stop(self, block: bool = True):
        if self.state != NodeState.RUNNING:
            self.log.warning("Node can't be stopped from non-running state")
            return
        
        self.shutdown_signal.set()
        
        if block and self.thread and self.thread.is_alive():
            self.thread.join()

    def run(self):
        with self.logging_context.bound_vars(thread=self.__class__.__name__):
            try:
                self.startup()
                self.startup_signal.set()
                self.shutdown_signal.wait()
                
            finally:
                self.shutdown()
                if self.err:
                    raise self.err
        
    def startup(self):
        self.state = NodeState.STARTING
        self.log.info("Starting node...")
        for comp_name in self.artifact.start_order:
            comp = getattr(self.container, comp_name)
            start_func = getattr(comp, START_FUNC_NAME)
            self.log.info(f"Starting {comp_name}...")
            
            try:
                start_func()
            except Exception as err:
                self.shutdown_signal.set()
                self.log.error(str(err))
                self.err = err
            
            if self.shutdown_signal.is_set():
                self.log.error(f"Startup failed, aborting")
                return
        
        self.state = NodeState.RUNNING
        self.log.info("Startup complete!")
            
    def shutdown(self):
        self.state = NodeState.STOPPING
        self.log.info("Stopping node...")
        for comp_name in self.artifact.stop_order:
            comp = getattr(self.container, comp_name)
            stop_func = getattr(comp, STOP_FUNC_NAME)
            self.log.info(f"Stopping {comp_name}...")
            stop_func()
        
        self.shutdown_signal.clear()
        self.state = NodeState.IDLE
        self.log.info("Shutdown complete!")
        
        try:
            exc = self.exception_queue.get_nowait()
            self.log.info("Raising queued error...")
            raise exc
        except Empty:
            pass
