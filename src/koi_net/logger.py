from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import colorama
import structlog
import sys
# from sentry_sdk import logger as sentry_logger


def my_processor(_, __, event: dict):
    # print(_, __, event)
    event["path"] = event["module"] + "." + event["func_name"]
    return event

# def sentry_processor(_, method, event: dict):
#     print(event)
#     if method == "critical":
#         sentry_logger.fatal(
#             event["event"],
#             attributes=event
#         )
#     elif method == "info":
#         sentry_logger.info(
#             event["event"],
#             attributes=event
#         )
#     elif method == "debug":
#         sentry_logger.debug(
#             event["event"],
#             attributes=event
#         )
#     return event

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
)

structlog.configure(
    processors=[
        # If log level is too low, abort pipeline and throw away log entry.
        structlog.stdlib.filter_by_level,
        # Add the name of the logger to event dict.
        structlog.stdlib.add_logger_name,
        # Add log level to event dict.
        structlog.stdlib.add_log_level,
        # Perform %-style formatting.
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Add a timestamp in ISO 8601 format.
        structlog.processors.TimeStamper(fmt="iso"),
        # If the "stack_info" key in the event dict is true, remove it and
        # render the current stack trace in the "stack" key.
        structlog.processors.StackInfoRenderer(),
        # If the "exc_info" key in the event dict is either true or a
        # sys.exc_info() tuple, remove "exc_info" and render the exception
        # with traceback into the "exception" key.
        # structlog.processors.format_exc_info,
        # If some value is in bytes, decode it to a Unicode str.
        structlog.processors.UnicodeDecoder(),
        # Add callsite parameters.
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.MODULE,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                # structlog.processors.CallsiteParameter.LINENO,
            }
        ),
        my_processor,
        # Render the final event dict as JSON.
        # sentry_processor,
        console_renderer
        # structlog.processors.JSONRenderer()
        
    ],
    # `wrapper_class` is the bound logger that you get back from
    # get_logger(). This one imitates the API of `logging.Logger`.
    wrapper_class=structlog.stdlib.BoundLogger,
    # `logger_factory` is used to create wrapped loggers that are used for
    # OUTPUT. This one returns a `logging.Logger`. The final value (a JSON
    # string) from the final processor (`JSONRenderer`) will be passed to
    # the method of the same name as that you've called on the bound logger.
    logger_factory=structlog.stdlib.LoggerFactory(),
    # Effectively freeze configuration after creating the first bound
    # logger.
    cache_logger_on_first_use=True,
)

file_handler = RotatingFileHandler(
    filename="app.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# log = structlog.stdlib.get_logger()