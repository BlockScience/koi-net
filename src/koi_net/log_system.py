import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Callable

import structlog
import colorama


class LogSystem:
    """Configures and initializes the logging system."""

    shared_log_processors: list[Callable] = [
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
    
    use_file_handler: bool
    use_console_handler: bool
    file_handler_log_level: int
    console_handler_log_level: int
    
    log_file_path: str
    max_log_file_size: int
    num_log_file_backups: int
    log_file_encoding: str
    
    def __init__(
        self,
        use_file_handler: bool = True,
        use_console_handler: bool = True,
        file_handler_log_level: int = logging.DEBUG,
        console_handler_log_level: int = logging.INFO,
        log_file_path: str = "log.ndjson",
        max_log_file_size: int = 10 * 1024 ** 2,
        num_log_file_backups: int = 5,
        log_file_encoding: str = "utf-8"
    ):
        self.use_file_handler = use_file_handler
        self.use_console_handler = use_console_handler
        self.file_handler_log_level = file_handler_log_level
        self.console_handler_log_level = console_handler_log_level
        
        self.log_file_path = log_file_path
        self.max_log_file_size = max_log_file_size
        self.num_log_file_backups = num_log_file_backups
        self.log_file_encoding = log_file_encoding
        
        self.configure()
        
    def configure(self):
        handlers = []
        if self.use_file_handler:
            handlers.append(self.configure_file_handler())
        if self.use_console_handler:
            handlers.append(self.configure_console_handler())
        
        logging.basicConfig(level=logging.DEBUG, handlers=handlers)
        structlog.configure(
            processors=self.shared_log_processors + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
    def configure_file_handler(self):
        file_handler = RotatingFileHandler(
            filename=self.log_file_path,
            maxBytes=self.max_log_file_size,
            backupCount=self.num_log_file_backups,
            encoding=self.log_file_encoding,
            delay=True
        )
        
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=self.shared_log_processors
            )
        )
        
        file_handler.setLevel(self.file_handler_log_level)
        return file_handler
    
    def configure_console_handler(self):
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
                foreign_pre_chain=self.shared_log_processors
            )
        )
        
        console_handler.setLevel(self.console_handler_log_level)
        return console_handler