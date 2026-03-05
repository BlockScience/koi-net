import threading
from logging import Logger
from pathlib import Path
from queue import Queue

import structlog
from structlog.contextvars import bound_contextvars

<<<<<<< Updated upstream:src/koi_net/base.py
from .infra import Assembler
from .components import LoggingContext
=======
from .assembler import NodeAssembler
from ..components import LoggingContext
>>>>>>> Stashed changes:src/koi_net/build/base.py


class BaseAssembly(Assembler):
    root_dir: Path
    
    shutdown_signal: threading.Event = threading.Event
    exception_queue: Queue[Exception] = lambda: Queue()

    log: Logger = lambda root_dir: structlog.stdlib.get_logger().bind(log_dir=root_dir)
    logging_context: LoggingContext = LoggingContext
    
    def __new__(cls, *args, root_dir: Path, **kwargs):
        cls.root_dir = root_dir
        with bound_contextvars(log_dir=root_dir):
            return super().__new__(cls, *args, **kwargs)
