import threading
from logging import Logger
from pathlib import Path

import structlog
from structlog.contextvars import bound_contextvars

from ..logging_context import LoggingContext
from .assembler import NodeAssembler


class BaseAssembly(NodeAssembler):
    root_dir: Path
    
    shutdown_signal: threading.Event = threading.Event

    log: Logger = lambda root_dir: structlog.stdlib.get_logger().bind(log_dir=root_dir)
    logging_context: LoggingContext = LoggingContext
    
    def __new__(cls, *args, root_dir: Path, **kwargs):
        cls.root_dir = root_dir
        with bound_contextvars(log_dir=root_dir):
            return super().__new__(cls, *args, **kwargs)
