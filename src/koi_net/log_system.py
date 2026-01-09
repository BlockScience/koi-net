from pathlib import Path
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Callable

import structlog
import colorama


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
    structlog.contextvars.merge_contextvars
]

class PartitionedFileHandler(logging.Handler):
    def __init__(
        self,
        log_file_name: str = "log.ndjson",
        max_log_file_size: int = 10 * 1024 ** 2,
        num_log_file_backups: int = 5,
        log_file_encoding: str = "utf-8"
    ):
        self.handlers: dict[str, RotatingFileHandler] = {}
        self.log_file_name = log_file_name
        self.max_log_file_size = max_log_file_size
        self.max_log_file_backups = num_log_file_backups
        self.log_file_encoding = log_file_encoding
        
        self.processor_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_log_processors
        )
        
        super().__init__()
        
    def get_handler(self, log_dir: str):
        if log_dir not in self.handlers:
            file_handler = RotatingFileHandler(
                filename=log_dir,
                maxBytes=self.max_log_file_size,
                backupCount=self.max_log_file_backups,
                encoding=self.log_file_encoding,
                delay=True
            )
            
            file_handler.setFormatter(self.processor_formatter)
            
            file_handler.setLevel(logging.DEBUG)
            self.handlers[log_dir] = file_handler
        
        return self.handlers[log_dir]
    
    def emit(self, record: logging.LogRecord):
        if record.log_dir is not None:
            log_dir = record.log_dir
            
        elif type(record.msg) is dict and "log_dir" in record.msg:
            log_dir = record.msg["log_dir"]
        
        else:
            print("FAILED EMIT:", record.msg)
            return
        
        log_dir_path = Path(log_dir) / Path(self.log_file_name)
        self.get_handler(str(log_dir_path)).emit(record)
        

class LogSystem:
    """Configures and initializes the logging system."""
    
    use_file_handler: bool
    use_console_handler: bool
    file_handler_log_level: int
    console_handler_log_level: int
    
    def __init__(
        self,
        use_file_handler: bool = True,
        use_console_handler: bool = True,
        file_handler_log_level: int = logging.DEBUG,
        console_handler_log_level: int = logging.DEBUG,
    ):
        self.use_file_handler = use_file_handler
        self.use_console_handler = use_console_handler
        self.file_handler_log_level = file_handler_log_level
        self.console_handler_log_level = console_handler_log_level
        
        self.configure()
        
    def configure(self):
        handlers = []
        if self.use_file_handler:
            handlers.append(PartitionedFileHandler())
        if self.use_console_handler:
            handlers.append(self.configure_console_handler())
        
        logging.basicConfig(level=logging.DEBUG, handlers=handlers)
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, *kwargs)
            
            ctx = structlog.contextvars.get_contextvars()
            record.log_dir = ctx.get("log_dir")
            
            return record
        
        logging.setLogRecordFactory(record_factory)
        
        structlog.configure(
            processors=shared_log_processors + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
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
                foreign_pre_chain=shared_log_processors
            )
        )
        
        console_handler.setLevel(self.console_handler_log_level)
        return console_handler