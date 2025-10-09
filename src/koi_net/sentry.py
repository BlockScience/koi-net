# import sentry_sdk
# from sentry_sdk.integrations.logging import LoggingIntegration

# sentry_sdk.init(
#     dsn="https://7bbafef3c7dbd652506db3cb2aca9f98@o4510149352357888.ingest.us.sentry.io/4510149355765760",
#     # Add data like request headers and IP for users,
#     # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
#     send_default_pii=True,
#     enable_logs=True,
#     integrations=[
#         LoggingIntegration(sentry_logs_level=None)
#     ]
# )