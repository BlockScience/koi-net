from .processor.handler_context import HandlerContext
from rid_lib.types import KoiNetNode
from rid_lib.ext import Bundle
from .effector import Effector


@Effector.register_default_action(KoiNetNode)
def dereference_koi_node(ctx: HandlerContext, rid: KoiNetNode) -> Bundle:
    if rid != ctx.identity.rid:
        return
    
    return Bundle.generate(
        rid=ctx.identity.rid,
        contents=ctx.identity.profile.model_dump()
    )