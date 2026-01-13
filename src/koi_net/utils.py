from functools import wraps
from pathlib import Path

import structlog
from structlog.contextvars import bound_contextvars

log = structlog.stdlib.get_logger()


def bind_logdir(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        root_dir = getattr(self, "root_dir", None)
        if not root_dir:
            root_dir = Path.cwd()
            log.warning(f"Failed to find `root_dir`, falling back to {root_dir} for `log_dir`", log_dir=root_dir)
        with bound_contextvars(log_dir=root_dir):
            return func(self, *args, **kwargs)
    return wrapper