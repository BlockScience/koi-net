from .consts import COMP_ORDER_OVERRIDE, CompOrder


def start_after(*comps):
    def decorator(func):
        func.start_after = list(comps)
        return func
    return decorator