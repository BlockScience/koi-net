import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

import structlog
import colorama


class LogSystem:
    """Handles initializing the logging system."""
    
    COMMON_PROCESSORS = [
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
    
    def __init__(self):
        self.setup_logging()
        
    def console_handler(self):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(
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
                        # structlog.dev.Column(
                        #     "func_name",
                        #     structlog.dev.KeyValueColumnFormatter(
                        #         key_style=None,
                        #         value_style=colorama.Fore.MAGENTA,
                        #         reset_style=colorama.Style.RESET_ALL,
                        #         value_repr=str,
                        #         prefix="(",
                        #         postfix=")",
                        #         width=15
                        #     ),
                        # ),
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
                ),
                foreign_pre_chain=self.COMMON_PROCESSORS
            )
        )
        
        return console_handler
    
        
        
    def file_handler(self):
        file_handler = RotatingFileHandler(
            filename="log.ndjson",
            maxBytes=10 * 1024 ** 2,
            backupCount=50,
            encoding="utf-8"
        )
        
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=self.COMMON_PROCESSORS
            )
        )
        
        return file_handler
        
    def setup_logging(self):
        handlers = [
            self.file_handler(),
            self.console_handler()
        ]
        
        logging.basicConfig(level=logging.DEBUG, handlers=handlers)
        
        structlog.configure(
            processors=self.COMMON_PROCESSORS + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
    def get_logger(self):
        return structlog.stdlib.get_logger()
