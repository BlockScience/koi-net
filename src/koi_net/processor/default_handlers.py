import logging
from rid_lib.ext import Bundle
from rid_lib.types import KoiNetNode, KoiNetEdge
from .interface import ProcessorInterface, NormalizedType
from ..protocol.event import EventType

logger = logging.getLogger(__name__)


@ProcessorInterface.as_handler(
    handler_type="state",
    order="after-cache",
    rid_types=[KoiNetNode, KoiNetEdge])
def koi_net_graph_handler(processor: ProcessorInterface, bundle, normalized_type):
    processor.network.graph.generate()
    return bundle, normalized_type
    

@ProcessorInterface.as_handler(
    handler_type="state", 
    order="decider")
def basic_state_handler(
    processor: ProcessorInterface, 
    bundle: Bundle, 
    normalized_type: NormalizedType
) -> NormalizedType:
    if processor.cache.exists(bundle.manifest.rid):
        logger.info("RID known to cache")
        prev_bundle = processor.cache.read(bundle.manifest.rid)

        if bundle.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
            logger.info("No change in knowledge, ignoring")
            return None # same knowledge
        if bundle.manifest.timestamp <= prev_bundle.manifest.timestamp:
            logger.info("Older manifest, ignoring")
            return None # incoming state is older
        
        logger.info(f"Newer manifest, writing {bundle.manifest.rid} to cache")
        # processor.cache.write(bundle)
        normalized_type = EventType.UPDATE

    else:
        logger.info(f"RID unknown to cache, writing {bundle.manifest.rid} to cache")
        # processor.cache.write(bundle)
        normalized_type = EventType.NEW
        
    return normalized_type
    

# p = ProcessorInterface()

# d = HandlerArgs(handler_type="event", target="before-cache", rid_types=(KoiNetNode))

# def foo(**kwargs: Unpack[HandlerArgs]):
#     ...
    
# foo(handler_type="", target="t", rid_types=(KoiNetNode,))