from typing import Callable

from rid_lib import RID
from rid_lib.ext import Bundle, Cache

cache = Cache()

def build_dereferencer(
    *funcs: list[Callable[[RID], Bundle | None]]
) -> Callable[[RID], Bundle | None]:
    def any_of(rid: RID):
        return any(
            f(rid) for f in funcs
        )
    return any_of

deref = build_dereferencer(cache.read)
deref(RID.from_string("string:hello_world"))