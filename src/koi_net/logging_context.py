from pathlib import Path

from structlog.contextvars import bound_contextvars


class LoggingContext:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        
    def bound_vars(self, thread: str):
        return bound_contextvars(log_dir=self.root_dir, thread=thread)