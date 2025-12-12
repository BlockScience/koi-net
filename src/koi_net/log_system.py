"""Configures and initializes the logging system."""

import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

import structlog
import colorama

LOG_FILE_PATH = "log.ndjson"
MAX_LOG_SIZE = 10 * 1024 ** 2 # 10MB
MAX_LOG_BACKUPS = 5
LOG_ENCODING = "utf-8"


shared_log_processors = [
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.UnicodeDecoder(),
    structlog.processors.CallsiteParameterAdder({
        structlog.processors.CallsiteParameter.MODULE,
        structlog.processors.CallsiteParameter.FUNC_NAME
    }),
]

console_renderer = structlog.dev.ConsoleRenderer(
    columns=[
        # Render the timestamp without the key name in yellow.
        structlog.dev.Column(
            "timestamp",
            structlog.dev.KeyValueColumnFormatter(
                key_style=None,
                value_style=colorama.Style.DIM,
                reset_style=colorama.Style.RESET_ALL,
                value_repr=lambda t: datetime.fromisoformat(t).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        ),
        structlog.dev.Column(
            "level",
            structlog.dev.LogLevelColumnFormatter(
                level_styles={
                    level: colorama.Style.BRIGHT + color
                    for level, color in {
                        "critical": colorama.Fore.RED,
                        "exception": colorama.Fore.RED,
                        "error": colorama.Fore.RED,
                        "warn": colorama.Fore.YELLOW,
                        "warning": colorama.Fore.YELLOW,
                        "info": colorama.Fore.GREEN,
                        "debug": colorama.Fore.GREEN,
                        "notset": colorama.Back.RED,
                    }.items()
                },
                reset_style=colorama.Style.RESET_ALL,
                width=9
            )
        ),
        # Render the event without the key name in bright magenta.
        
        # Default formatter for all keys not explicitly mentioned. The key is
        # cyan, the value is green.
        structlog.dev.Column(
            "path",
            structlog.dev.KeyValueColumnFormatter(
                key_style=None,
                value_style=colorama.Fore.MAGENTA,
                reset_style=colorama.Style.RESET_ALL,
                value_repr=str,
                width=30
            ),
        ),
        structlog.dev.Column(
            "event",
            structlog.dev.KeyValueColumnFormatter(
                key_style=None,
                value_style=colorama.Fore.WHITE,
                reset_style=colorama.Style.RESET_ALL,
                value_repr=str,
                width=30
            ),
        ),
        structlog.dev.Column(
            "",
            structlog.dev.KeyValueColumnFormatter(
                key_style=colorama.Fore.BLUE,
                value_style=colorama.Fore.GREEN,
                reset_style=colorama.Style.RESET_ALL,
                value_repr=str,
            ),
        )
    ]
)


console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(
    structlog.stdlib.ProcessorFormatter(
        processor=console_renderer,
        foreign_pre_chain=shared_log_processors
    )
)

file_handler = RotatingFileHandler(
    filename=LOG_FILE_PATH,
    maxBytes=MAX_LOG_SIZE,
    backupCount=MAX_LOG_BACKUPS,
    encoding=LOG_ENCODING
)

file_handler.setFormatter(
    structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_log_processors
    )
)

logging.basicConfig(
    level=logging.DEBUG, 
    handlers=[
        file_handler,
        console_handler
    ])

structlog.configure(
    processors=shared_log_processors + [
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)