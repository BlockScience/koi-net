import logging
from rid_lib.ext import Bundle
from rid_lib.types import KoiNetNode, KoiNetEdge
from .interface import ProcessorInterface, HandlerType, InternalEvent
from ..protocol import Event, EventType, EdgeModel

logger = logging.getLogger(__name__)


@ProcessorInterface.as_handler(
    handler_type=HandlerType.Network,
    rid_types=[KoiNetNode, KoiNetEdge])
def koi_net_graph_handler(processor: ProcessorInterface, ievent: InternalEvent):
    processor.network.graph.generate()
    return ievent
    

@ProcessorInterface.as_handler(handler_type=HandlerType.Manifest)
def basic_state_handler(processor: ProcessorInterface, ievent: InternalEvent):
    prev_bundle = processor.cache.read(ievent.rid)

    if prev_bundle:
        if ievent.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
            logger.info("Hash of incoming manifest is same as existing knowledge, ignoring")
            return # same knowledge
        if ievent.manifest.timestamp <= prev_bundle.manifest.timestamp:
            logger.info("Timestamp of incoming manifest is older than existing knowledge, ignoring")
            return # incoming state is older
        
        logger.info("Knowledge previously known to me, labeling as 'UPDATE'")
        ievent.normalized_event_type = EventType.UPDATE

    else:
        logger.info("Knowledge previously unknown to me, labeling as 'NEW'")
        ievent.normalized_event_type = EventType.NEW
        
    return ievent

@ProcessorInterface.as_handler(HandlerType.Network)
def basic_network_output_filter(processor: ProcessorInterface, ievent: InternalEvent):
    if type(ievent.rid) in processor.my.profile.provides.event:
        return ievent
    else:
        logger.info(f"I don't provide events for {type(ievent.rid)}, blocking broadcast")
        return


@ProcessorInterface.as_handler(HandlerType.Final, rid_types=[KoiNetEdge])
def edge_negotiation_handler(processor: ProcessorInterface, ievent: InternalEvent):
    edge_profile = EdgeModel.model_validate(ievent.contents)

    logger.info("Handling edge negotiation")

    # indicates peer subscriber
    if edge_profile.source == processor.my.rid:                
        if edge_profile.status != "proposed":
            # TODO: handle other status
            return ievent
        
        if any(rid_type not in processor.my.profile.provides.event for rid_type in edge_profile.rid_types):
            # indicates node subscribing to unsupported event
            # TODO: either reject or repropose agreement
            logger.info("Requested RID types not provided by this node")
            event = Event.from_rid(EventType.FORGET, event.rid)

            
        elif not processor.cache.read(edge_profile.target):
            # TODO: handle unknown subscriber node (delete edge?)
            logger.warning("Peer unknown to this node")
            event = Event.from_bundle(EventType.FORGET, event.rid)

        else:
            # approve edge profile
            edge_profile.status = "approved"
            updated_bundle = Bundle.generate(ievent.rid, edge_profile.model_dump())
            
            event = Event.from_bundle(EventType.UPDATE, updated_bundle)
            
        processor.network.push_event_to(event, edge_profile.target, flush=True)
        processor.handle_event(event)
        
    elif edge_profile.target == processor.my.rid:
        logger.info("Edge approved by other node!")
        
    return ievent
