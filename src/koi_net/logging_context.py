from dataclasses import dataclass
from pathlib import Path

from structlog.contextvars import bound_contextvars


@dataclass
class LoggingContext:
    root_dir: Path
    
    def bound_vars(self, thread: str):
        return bound_contextvars(log_dir=self.root_dir, thread=thread)