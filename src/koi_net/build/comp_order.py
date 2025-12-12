from .consts import COMP_ORDER_OVERRIDE, CompOrder


def worker(cls):
    setattr(cls, COMP_ORDER_OVERRIDE, CompOrder.WORKER)
    return cls