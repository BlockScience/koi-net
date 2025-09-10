"""Implementations of default dereference actions."""

from .context import ActionContext
from rid_lib.types import KoiNetNode
from rid_lib.ext import Bundle
from .effector import Effector


@Effector.register_default_action(KoiNetNode)
def dereference_koi_node(
    ctx: ActionContext, rid: KoiNetNode
) -> Bundle | None:
    """Dereference function for this KOI node.
    
    Generates a bundle from this node's profile data in the config.
    """
    
    if rid != ctx.identity.rid:
        return
    
    return Bundle.generate(
        rid=ctx.identity.rid,
        contents=ctx.identity.profile.model_dump()
    )