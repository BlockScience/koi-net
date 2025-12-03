from enum import StrEnum


START_FUNC_NAME = "start"
STOP_FUNC_NAME = "stop"

START_ORDER_OVERRIDE = "_start_order"
STOP_ORDER_OVERRIDE = "_stop_order"

COMP_TYPE_OVERRIDE = "_comp_type"
COMP_ORDER_OVERRIDE = "_comp_order"

class CompType(StrEnum):
    SINGLETON = "SINGLETON"
    OBJECT = "OBJECT"

class CompOrder(StrEnum):
    WORKER = "WORKER"