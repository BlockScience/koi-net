# KOI-net

*This specification is the result of several iterations of KOI research, [read more here](https://github.com/BlockScience/koi).*

### Jump to Sections: 
- [Protocol](#protocol)
    - [Introduction](#introduction)
    - [Communication Methods](#communication-methods)
- [Quickstart](#quickstart)
    - [Setup](#setup)
    - [Creating a Node](#creating-a-node)
    - [Knowledge Processing](#knowledge-processing)
    - [Try It Out!](#try-it-out)
- [Advanced](#advanced)
    - [Knowledge Processing Pipeline](#knowledge-processing-pipeline)
    - [Knowledge Handlers](#knowledge-handlers)
        - [RID Handler](#rid-handler)
        - [Manifest Handler](#manifest-handler)
        - [Bundle Handler](#bundle-handler)
        - [Network Handler](#network-handler)
        - [Final Handler](#final-handler)
    - [Registering Handlers](#registering-handlers)
    - [Default Behavior](#default-behavior)
- [Implementation Reference](#implementation-reference)
    - [Node Interface](#node-interface)
    - [Node Identity](#node-identity)
    - [Network Interface](#network-interface)
        - [Network Graph](#network-graph)
        - [Request Handler](#request-handler)
        - [Response Handler](#response-handler)
    - [Processor Interface](#processor-interface)
- [Development](#development)
    - [Setup](#setup-1)
    - [Distribution](#distribution)

# Protocol
## Introduction

*This project builds upon and uses the [RID protocol](https://github.com/BlockScience/rid-lib) to identify and coordinate around knowledge objects.*

This protocol defines the standard communication patterns and coordination norms needed to establish and maintain Knowledge Organization Infrastructure (KOI) networks. KOI-nets are heterogenous compositions of KOI nodes, each of which is capable of autonomously inputting, processing, and outputting knowledge. The behavior of each node and configuration of each network can vary greatly, thus the protocol is designed to be a simple and flexible but interoperable foundation for future projects to build on. The protocol only governs communication between nodes, not how they operate internally. As a result we consider KOI-nets to be fractal-like, in that a network of nodes may act like a single node from an outside perspective.

Generated OpenAPI documentation is provided in this repository, and can be [viewed interactively with Swagger](https://generator.swagger.io/?url=https://raw.githubusercontent.com/BlockScience/koi-net/refs/heads/main/koi-net-protocol-openapi.json).

## Communication Methods

There are two classes of communication methods, event and state communication. 
- Event communication is one way, a node send an event to another node. 
- State communication is two way, a node asks another node for RIDs, manifests, or bundles and receives a response containing the requested resource (if available).

There are also two types of nodes, full and partial nodes. 
- Full nodes are web servers, implementing the endpoints defined in the KOi-net protocol. They are capable of receiving events via webhooks (another node calls their endpoint), and serving state queries. They can also call the endpoints of other full nodes to broadcast events or retrieve state. 
- Partial nodes are web clients and don't implement any API endpoints. They are capable of receiving events via polling (asking another node for events). They can also call the endpoints of full nodes to broadcast events or retrieve state.

There are five endpoints defined by the API spec. The first two are for event communication with full and partial nodes respectively. The remaining three are for state communication with full nodes. As a result, partial nodes are unable to directly transfer state and may only output events to other nodes.
- Broadcast events - `/events/broadcast`
- Poll events - `/events/poll`
- Fetch bundles - `/bundles/fetch`
- Fetch manifests - `/manifests/fetch`
- Fetch RIDs - `/rids/fetch`

All endpoints are called with via POST request with a JSON body, and will receive a response containing a JSON payload (with the exception of broadcast events, which won't return anything). The JSON schemas can be found in the attached OpenAPI specification or the Pydantic models in the "protocol" module.

The request and payload JSON objects are composed of the fundamental "knowledge types" from the RID / KOI-net system: RIDs, manifests, bundles, and events. RIDs, manifests, and bundles are defined by the RID protocol and imported from rid-lib, which you can [read about here](https://github.com/BlockScience/rid-lib). Events are now part of the KOI-net protocol, and are defined as an RID and an event type with an optional manifest and contents. 

```json
{
    "rid": "...",
    "event_type": "NEW | UPDATE | FORGET",
    "manifest": {
        "rid": "...",
        "timestamp": "...",
        "sha256_hash": "...",
    },
    "contents": {}
}
```

An event is a signalling construct that conveys information about RID objects between networked nodes. Events are composed of an RID, manifest, or bundle with an event type attached. Event types can be one of `"FORGET"`, `"UPDATE"`, or `"NEW"` forming the "FUN" acronym. 

As opposed to CRUD (create, read, update, delete), events are a series of messages, not operations. Each node has its own autonomy in deciding how to react based on the message it receives. For example, a processor node may receive a `"NEW"` event for an RID object its not interested in, and ignore it. Or it may decide that an `"UPDATE"` event should trigger fetching a bundle from another node. A node emits an event to indicate that its internal state has changed:
- `"NEW"` - indicates an previously unknown RID was cached
- `"UPDATE"` - indicates a previously known RID was cached
- `"FORGET"` - indicates a previously known RID was deleted

Nodes may broadcast events to other nodes to indicate their internal state changed. Conversely, nodes may also listen to events from other nodes and as a result decide to change their internal state, take some other action, or do nothing.


# Quickstart
## Setup

The bulk of the code in this repo is taken up by the Python reference implementation, which can be used in other projects to easily set up and configure your own KOI-net node.

This package can be installed with pip:
```shell
pip install koi-net
```

## Creating a Node

*Check out the `examples/` folder to follow along!*

All of the KOI-net functionality comes from the `NodeInterface` class which provides methods to interact with the protocol API, a local RID cache, a view of the network, and an internal processing pipeline. To create a new node, you will need to give it a name and a profile. The name will be used to generate its unique node RID, and the profile stores basic configuration data which will be shared with the other nodes that you communciate with.

Your first decision will be whether to setup a partial or full node:
- Partial nodes only need to indicate their type, and optionally the RID types of events they provide.
- Full nodes need to indicate their type, the base URL for their KOI-net API, and optionally the RID types of events and state they provide.

Nodes are configured using the provided `NodeConfig` class. Defaults can be set as shown below, and will automatically load from and save to YAML files. See the `koi_net.config` module for more info.

### Partial Node
```python
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeProvides, NodeType
from koi_net.config import NodeConfig, KoiNetConfig

class CoordinatorNodeConfig(NodeConfig):
    koi_net: KoiNetConfig | None = Field(default_factory = lambda:
        KoiNetConfig(
            node_name="coordinator",
            node_profile=NodeProfile(
                node_type=NodeType.FULL
            ),
            cache_directory_path=".basic_partial_rid_cache",
            event_queues_path="basic_partial_event_queues.json",
            first_contact="http://127.0.0.1:8000/koi-net"
        )
    )


node = NodeInterface(
    config=CoordinatorNodeConfig.load_from_yaml("basical_partial_config.yaml")
)
```
### Full Node
```python
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeProvides, NodeType
from koi_net.config import NodeConfig, KoiNetConfig

class CoordinatorNodeConfig(NodeConfig):
    koi_net: KoiNetConfig | None = Field(default_factory = lambda:
        KoiNetConfig(
            node_name="coordinator",
            node_profile=NodeProfile(
                node_type=NodeType.FULL,
                provides=NodeProvides(
                    event=[KoiNetNode, KoiNetEdge],
                    state=[KoiNetNode, KoiNetEdge]
                )
            ),
            cache_directory_path=".coordinator_rid_cache",
            event_queues_path="coordinator_event_queues.json"
        )
    )

node = NodeInterface(
    config=CoordinatorNodeConfig.load_from_yaml("coordinator_config.yaml"),
    use_kobj_processor_thread=True
)
```

When creating a node, you optionally enable `use_kobj_processor_thread` which will run the knowledge processing pipeline on a separate thread. This thread will automatically dequeue and process knowledge objects as they are added to the `kobj_queue`, which happenes when you call `node.process.handle(...)`. This is required to prevent race conditions in asynchronous applications, like web servers, therefore it is recommended to enable this feature for all full nodes. 

## Knowledge Processing

Next we'll set up the knowledge processing flow for our node. This is where most of the node's logic and behavior will come into play. For partial nodes this will be an event loop, and for full nodes we will use webhooks. Make sure to call `node.start()` and `node.stop()` at the beginning and end of your node's life cycle.

### Partial Node
Make sure to set `source=KnowledgeSource.External` when calling `handle` on external knowledge, this indicates to the knowledge processing pipeline that the incoming knowledge was received from another node. Where the knowledge is sourced from will impact decisions in the node's knowledge handlers.
```python
import time
from koi_net.processor.knowledge_object import KnowledgeSource

if __name__ == "__main__":
    node.start()

    try:
        while True:
            for event in node.network.poll_neighbors():
                node.processor.handle(event=event, source=KnowledgeSource.External)
            node.processor.flush_kobj_queue()
            
            time.sleep(5)
            
    finally:
        node.stop()
```

### Full Node
Setting up a full node is slightly more complex as we'll need a webserver. For this example, we'll use FastAPI and uvicorn. First we need to setup the "lifespan" of the server, to start and stop the node before and after execution, as well as the FastAPI app which will be our web server.
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    node.start()
    yield
    node.stop()


app = FastAPI(lifespan=lifespan, root_path="/koi-net")
```

Next we'll add our event handling webhook endpoint, which will allow other nodes to broadcast events to us. You'll notice that we have a similar loop to our partial node, but instead of polling periodicially, we handle events asynchronously as we receive them from other nodes.

```python
from koi_net.protocol.api_models import *
from koi_net.protocol.consts import *

@app.post(BROADCAST_EVENTS_PATH)
def broadcast_events(req: EventsPayload):
    for event in req.events:
        node.processor.handle(event=event, source=KnowledgeSource.External)
```

Next we can add the event polling endpoint, this allows partial nodes to receive events from us.

```python
@app.post(POLL_EVENTS_PATH)
def poll_events(req: PollEvents) -> EventsPayload:
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)
```

Now for the state transfer "fetch" endpoints:
```python
@app.post(FETCH_RIDS_PATH)
def fetch_rids(req: FetchRids) -> RidsPayload:
    return node.network.response_handler.fetch_rids(req)

@app.post(FETCH_MANIFESTS_PATH)
def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
    return node.network.response_handler.fetch_manifests(req)

@app.post(FETCH_BUNDLES_PATH)
def fetch_bundles(req: FetchBundles) -> BundlesPayload:
    return node.network.response_handler.fetch_bundles(req)
```

Finally we can run the server!

```python
import uvicorn

if __name__ == "__main__":
    # update this path to the Python module that defines "app"
    uvicorn.run("examples.full_node_template:app", port=8000)
```

*Note: If your node is not the first node in the network, you'll also want to set up a "first contact" in the `NodeInterface`. This is the URL of another full node that can be used to make your first connection and find out about other nodes in the network.*

## Try It Out!

In addition to the partial and full node templates, there's also example implementations that showcase a coordinator + partial node setup. You can run both of them locally after cloning this repository. First, install the koi-net library with the optional examples requirements from the root directory in the repo:
```shell
pip install .[examples]
```
Then you can start each node in a separate terminal:
```shell
python -m examples.basic_coordinator_node
```
```shell
python -m examples.basic_partial_node
```

# Advanced

## Knowledge Processing Pipeline
Beyond the `NodeInterface` setup and boiler plate for partial/full nodes, node behavior is mostly controlled through the use of knowledge handlers. Effectively creating your own handlers relies on a solid understanding of the knowledge processing pipeline, so we'll start with that. As a developer, you will interface with the pipeline through the `ProcessorInterface` accessed with `node.processor`. The pipeline handles knowledge objects, from the `KnowledgeObject` class, a container for all knowledge types in the RID / KOI-net ecosystem:
- RIDs
- Manifests
- Bundles
- Events

Here is the class definition for a knowledge object:
```python
type KnowledgeEventType = EventType | None

class KnowledgeSource(StrEnum):
    Internal = "INTERNAL"
    External = "EXTERNAL"

class KnowledgeObject(BaseModel):
    rid: RID
    manifest: Manifest | None = None
    contents: dict | None = None
    event_type: KnowledgeEventType = None
    source: KnowledgeSource
    normalized_event_type: KnowledgeEventType = None
    network_targets: set[KoiNetNode] = set()
```

In addition to the fields required to represent the knowledge types (`rid`, `manifest`, `contents`, `event_type`), knowledge objects also include a `source` field, indicating whether the knowledge originated from within the node (`KnowledgeSource.Internal`) or from another node (`KnowledgeSource.External`).

The final two fields are not inputs, but are set by handlers as the knowledge object moves through the processing pipeline. The normalized event type indicates the event type normalized to the perspective of the node's cache, and the network targets indicate where the resulting event should be broadcasted to.

Knowledge objects enter the processing pipeline through the `node.processor.handle(...)` method. Using kwargs you can pass any of the knowledge types listed above, a knowledge source, and an optional `event_type` (for non-event knowledge types). The handle function will simply normalize the provided knowledge type into a knowledge object, and put it in the `kobj_queue`, an internal, thread-safe queue of knowledge objects. If you have enabled `use_kobj_processor_thread` then the queue will be automatically processed on the processor thread, otherwise you will need to regularly call `flush_kobj_queue` to process queued knowledge objects (as in the partial node example). Both methods will process knowledge objects sequentially, in the order that they were queued in (FIFO). 


## Knowledge Handlers

Processing happens through five distinct phases, corresponding to the handler types: `RID`, `Manifest`, `Bundle`, `Network`, and `Final`. Each handler type can be understood by describing (1) what knowledge object fields are available to the handler, and (2) what action takes place after this phase, which the handler can influence. As knowledge objects pass through the pipeline, fields may be added or updated. 

Handlers are registered in a single handler array within the processor. There is no limit to the number of handlers in use, and multiple handlers can be assigned to the same handler type. At each phase of knowledge processing, we will chain together all of the handlers of the corresponding type and run them in their array order. The order handlers are registered in matters!

Each handler will be passed a knowledge object. They can choose to return one of three types: `None`, `KnowledgeObject`, or `STOP_CHAIN`. Returning `None` will pass the unmodified knowledge object (the same one the handler received) to the next handler in the chain. If a handler modified their knowledge object, they should return it to pass the new version to the next handler. Finally, a handler can return `STOP_CHAIN` to immediately stop processing the knowledge object. No further handlers will be called and it will not enter the next phase of processing.

Summary of processing pipeline:
```
RID -> Manifest -> Bundle -> [cache action] -> Network -> [network action] -> Final
           |
(skip if event type is "FORGET")
```

### RID Handler
The knowledge object passed to handlers of this type are guaranteed to have an RID and knowledge source field. This handler type acts as a filter, if none of the handlers return `STOP_CHAIN` the pipeline will progress to the next phase. The pipeline diverges slightly after this handler chain, based on the event type of the knowledge object.

If the event type is `"NEW"`, `"UPDATE"`, or `None` and the manifest is not already in the knowledge object, the node will attempt to retrieve it from (1) the local cache if the source is internal, or (2) from another node if the source is external. If it fails to retrieves the manifest, the pipeline will end. Next, the manifest handler chain will be called.

If the event type is `"FORGET"`, and the bundle (manifest + contents) is not already in the knowledge object, the node will attempt to retrieve it from the local cache, regardless of the source. In this case the knowledge object represents what we will delete from the cache, not new incoming knowledge. If it fails to retrieve the bundle, the pipeline will end. Next, the bundle handler chain will be called.

### Manifest Handler
The knowledge object passed to handlers of this type are guaranteed to have an RID, manifest, and knowledge source field. This handler type acts as a filter, if none of the handlers return `STOP_CHAIN` the pipeline will progress to the next phase.

If the bundle (manifest + contents) is not already in the knowledge object, the node will attempt to retrieve it from (1) the local cache if the source is internal, or (2) from another node if the source is external. If it fails to retrieve the bundle, the pipeline will end. Next, the bundle handler chain will be called.

### Bundle Handler
The knowledge object passed to handlers of this type are guaranteed to have an RID, manifest, bundle (manifest + contents), and knowledge source field. This handler type acts as a decider. In this phase, the knowledge object's normalized event type must be set to `"NEW"` or `"UPDATE"` to write it to cache, or `"FORGET"` to delete it from the cache. If the normalized event type remains unset (`None`), or a handler returns `STOP_CHAIN`, then the pipeline will end without taking any cache action.

The cache action will take place after the handler chain ends, so if multiple handlers set a normalized event type, the final handler will take precedence.

### Network Handler
The knowledge object passed to handlers of this type are guaranteed to have an RID, manifest, bundle (manifest + contents), normalized event type, and knowledge source field. This handler type acts as a decider. In this phase, handlers decide which nodes to broadcast this knowledge object to by appending KOI-net node RIDs to the knowledge object's `network_targets` field. If a handler returns `STOP_CHAIN`, the pipeline will end without taking any network action.

The network action will take place after the handler chain ends. The node will attempt to broadcast a "normalized event", created from the knowledge object's RID, bundle, and normalized event type, to all of the node's in the network targets array. 

### Final Handler
The knowledge object passed to handlers of this type are guaranteed to have an RID, manifest, bundle (manifest + contents), normalized event type, and knowledge source field.

This is the final handler chain that is called, it doesn't make any decisions or filter for succesive handler types. Handlers here can be useful if you want to take some action after the network broadcast has ended.

## Registering Handlers
Knowledge handlers are registered with a node's processor by decorating a handler function. There are two types of decorators, the first way converts the function into a handler object which can be manually added to a processor. This is how the default handlers are defined, and makes them more portable (could be imported from another package). The second automatically registers a handler with your node instance. This is not portable but more convenient. The input of the decorated function will be the processor instance, and a knowledge object.

```python
from .handler import KnowledgeHandler, HandlerType, STOP_CHAIN

@KnowledgeHandler.create(HandlerType.RID)
def example_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    ...

@node.processor.register_handler(HandlerType.RID)
def example_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    ...
```

While handler's only require specifying the handler type, you can also specify the RID types, knowledge source, or event types you want to handle. If a knowledge object doesn't match all of the specified parameters, it won't be called. By default, handlers will match all RID types, all event types, and both internal and external sourced knowledge.

```python
@KnowledgeHandler.create(
    handler_type=HandlerType.Bundle, 
    rid_types=[KoiNetEdge], 
    source=KnowledgeSource.External,
    event_types=[EventType.NEW, EventType.UPDATE])
def edge_negotiation_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    ...
```

The processor instance passed to your function should be used to take any necessary node actions (cache, network, etc.). It is also sometimes useful to add new knowledge objects to the queue while processing a different knowledge object. You can simply call `processor.handle(...)` in the same way as you would outside of a handler. It will put at the end of the queue and processed when it is dequeued like any other knowledge object.


## Default Behavior

The default configuration provides four default handlers which will take precedence over any handlers you add yourself. To override this behavior, you can set the `handlers` field in the `NodeInterface`:

```python
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeProvides, NodeType
from koi_net.config import NodeConfig
from koi_net.processor.default_handlers import (
    basic_rid_handler,
    basic_manifest_handler,
    edge_negotiation_handler,
    basic_network_output_filter
)

node = NodeInterface(
    config=NodeConfig.load_from_yaml(),
    handlers=[
        basic_rid_handler,
        basic_manifest_handler,
        edge_negotiation_handler,
        basic_network_output_filter

        # include all or none of the default handlers
    ]
)
```

Take a look at `src/koi_net/processor/default_handlers.py` to see some more in depth examples and better understand the default node behavior.

# Implementation Reference
This section provides high level explanations of the Python implementation. More detailed explanations of methods can be found in the docstrings within the codebase itself.

## Node Interface
The node class mostly acts as a container for other classes with more specialized behavior, with special functions that should be called to start up and shut down a node. We'll take a look at each of these components in turn, but here is the class stub:
```python
class NodeInterface:
    config: ConfigType
    cache: Cache
    identity: NodeIdentity
    network: NetworkInterface
    processor: ProcessorInterface
    
    use_kobj_processor_thread: bool
    
    def __init__(
        self, 
        config: ConfigType,
        use_kobj_processor_thread: bool = False,
        
        handlers: list[KnowledgeHandler] | None = None,
        
        cache: Cache | None = None,
        network: NetworkInterface | None = None,
        processor: ProcessorInterface | None = None
    ): ...

    def start(self): ...
    def stop(self): ...
```
As you can see, only a node config is required, all other fields are optional.

## Node Config

The node config class is a mix of configuration groups providing basic shared behavior across nodes through a standard interface. The class is implemented as Pydantic model, but provides functions to load from and save to a YAML file, the expected format within a node repo.

```python
class ServerConfig(BaseModel):
    host: str | None = "127.0.0.1"
    port: int | None = 8000
    path: str | None = "/koi-net"
    
    @property
    def url(self) -> str: ...

class KoiNetConfig(BaseModel):
    node_name: str
    node_rid: KoiNetNode | None = None
    node_profile: NodeProfile
    
    cache_directory_path: str | None = ".rid_cache"
    event_queues_path: str | None = "event_queues.json"

    first_contact: str | None = None

class EnvConfig(BaseModel):
    ...

class NodeConfig(BaseModel):
    server: ServerConfig | None = Field(default_factory=ServerConfig)
    koi_net: KoiNetConfig

    @classmethod
    def load_from_yaml(
        cls, 
        file_path: str = "config.yaml", 
        generate_missing: bool = True
    ): ...
    
    def save_to_yaml(self): ...
```

Nodes are expected to create new node config classes inheriting from `NodeConfig`. You may want to set a default KoiNetConfig (see examples) to allow for a default config to be generated if not provided by the user. Environment variables can be handled by inheriting from the `EnvConfig` class and adding new string fields. The value of this field should be equivalent to the environment variable name, for example:

```python
class SlackEnvConfig(EnvConfig):
    slack_bot_token: str | None = "SLACK_BOT_TOKEN"
    slack_signing_secret: str | None = "SLACK_SIGNING_SECRET"
    slack_app_token: str | None = "SLACK_APP_TOKEN"
```

This special config class will automatically load in the variables from the current environment, or local `.env` file. Beyond these base config classes, you are free to add your own config groups. See `config.py` in the [koi-net-slack-sensor-node](https://github.com/BlockScience/koi-net-slack-sensor-node/blob/main/slack_sensor_node/config.py) repo for a more complete example.

## Node Identity
The `NodeIdentity` class provides easy access to a node's own RID, profile, and bundle. It provides access to the following properties after initialization, accessed with `node.identity`.
```python
class NodeIdentity:
    rid: KoiNetNode # an RID type
    profile: NodeProfile
    bundle: Bundle
```
This it what is initialized from the required `name` and `profile` fields in the `NodeConfig` class. Node RIDs take the form of `orn:koi-net.node:<name>+<uuid>`, and are generated on first use to the identity JSON file along with a the node profile.

## Network Interface
The `NetworkInterface` class provides access to high level network actions, and contains several other network related classes. It is accessed with `node.network`.
```python
class NetworkInterface:
    graph: NetworkGraph
    request_handler: RequestHandler
    response_handler: ResponseHandler

    def __init__(
        self, 
        file_path: str,
        first_contact: str | None,
        cache: Cache, 
        identity: NodeIdentity
    ): ...

    def push_event_to(self, event: Event, node: KoiNetNode, flush=False): ...
    
    def flush_poll_queue(self, node: KoiNetNode) -> list[Event]: ...
    def flush_webhook_queue(self, node: RID): ...

    def fetch_remote_bundle(self, rid: RID): ...
    def fetch_remote_manifest(self, rid: RID): ...

    def get_state_providers(self, rid_type: RIDType): ...
    def poll_neighbors(self) -> list[Event]: ...
```

Most of the provided functions are abstractions for KOI-net protocol actions. It also contains three lower level classes: `NetworkGraph`, `RequestHandler`, and `ResponseHandler`.

### Network Graph
The `NetworkGraph` class provides access to a graph view of the node's KOI network: all of the KOI-net node and edge objects it knows about (stored in local cache). This view allows us to query nodes that we have edges with to make networking decisions.
```python
class NetworkGraph:
    dg: nx.DiGraph

    def __init__(
        self,
        cache: Cache,
        identity: NodeIdentity
    ): ...

    def generate(self): ...

    def get_edges(
        self, 
        direction: Literal["in", "out"] | None = None
    ) -> list[KoiNetEdge]: ...

    def get_neighbors(
        self,
        direction: Literal["in", "out"] | None = None,
        status: EdgeStatus | None = None,
        allowed_type: RIDType | None = None
    ) -> list[KoiNetNode]: ...
    
    def get_node_profile(self, rid: KoiNetNode) -> NodeProfile | None: ...
    def get_edge_profile(
        self,
        rid: KoiNetEdge | None = None,
        source: KoiNetNode | None = None,
        target: KoiNetNode | None = None
    ) -> EdgeProfile | None: ...
```

### Request Handler
Handles raw API requests to other nodes through the KOI-net protocol. Accepts a node RID or direct URL as the target. Each method requires either a valid request model, or `kwargs` which will be converted to the correct model in `koi_net.protocol.api_models`.
```python
class RequestHandler:
    def __init__(self, cache: Cache, graph: NetworkGraph): ...

    def broadcast_events(
        self, 
        node: RID = None, 
        url: str = None, 
        req: EventsPayload | None = None,
        **kwargs
    ) -> None: ...

    def poll_events(
        self, 
        node: RID = None, 
        url: str = None, 
        req: PollEvents | None = None,
        **kwargs
    ) -> EventsPayload: ...

    def fetch_rids(
        self, 
        node: RID = None, 
        url: str = None, 
        req: FetchRids | None = None,
        **kwargs
    ) -> RidsPayload: ...

    def fetch_manifests(
        self, 
        node: RID = None, 
        url: str = None, 
        req: FetchManifests | None = None,
        **kwargs
    ) -> ManifestsPayload: ...

    def fetch_bundles(
        self, 
        node: RID = None, 
        url: str = None, 
        req: FetchBundles | None = None,
        **kwargs
    ) -> BundlesPayload: ...
```

### Response Handler
Handles raw API responses to requests from other nodes through the KOI-net protocol.
```python
class ResponseHandler:
    def __init__(self, cache: Cache): ...

    def fetch_rids(self, req: FetchRids) -> RidsPayload:
    def fetch_manifests(self, req: FetchManifests) -> ManifestsPayload:
    def fetch_bundles(self, req: FetchBundles) -> BundlesPayload:
```
Only fetch methods are provided right now, event polling and broadcasting can be handled like this:
```python
def broadcast_events(req: EventsPayload) -> None:
    for event in req.events:
        node.processor.handle(event=event, source=KnowledgeSource.External)
    node.processor.flush_kobj_queue()

def poll_events(req: PollEvents) -> EventsPayload:
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)
```

## Processor Interface
The `ProcessorInterface` class provides access to a node's internal knowledge processing pipeline.
```python
class ProcessorInterface:
    worker_thread: threading.Thread | None = None

    def __init__(
        self, 
        cache: Cache, 
        network: NetworkInterface,
        identity: NodeIdentity,
        use_kobj_processor_thread: bool,
        default_handlers: list[KnowledgeHandler] = []
    ): ...

    def add_handler(self, handler: KnowledgeHandler): ...
    
    def register_handler(
        self,
        handler_type: HandlerType,
        rid_types: list[RIDType] | None = None
    ): ...

    def process_kobj(self, kobj: KnowledgeObject) -> None:
    def flush_kobj_queue(self): ...

    def handle(
        self,
        rid: RID | None = None,
        manifest: Manifest | None = None,
        bundle: Bundle | None = None,
        event: Event | None = None,
        kobj: KnowledgeObject | None = None,
        event_type: KnowledgeEventType = None,
        source: KnowledgeSource = KnowledgeSource.Internal
    ): ...
```

The `register_handler` method is a decorator which can wrap a function to create a new `KnowledgeHandler` and add it to the processing pipeline in a single step. The `add_handler` method adds an existing `KnowledgeHandler` to the processining pipeline.

The most commonly used functions in this class are `handle` and `flush_kobj_queue`. The `handle` method can be called on RIDs, manifests, bundles, and events to convert them to normalized to `KnowledgeObject` instances which are then added to the processing queue. If you have enabled `use_kobj_processor_thread` then the queue will be automatically processed, otherwise you will need to regularly call `flush_kobj_queue` to process queued knolwedge objects. When calling the `handle` method, knowledge objects are marked as internally source by default. If you are handling RIDs, manifests, bundles, or events sourced from other nodes, `source` should be set to `KnowledgeSource.External`.

Here is an example of how an event polling loop would be implemented using the knowledge processing pipeline:
```python
for event in node.network.poll_neighbors():
    node.processor.handle(event=event, source=KnowledgeSource.External)
node.processor.flush_kobj_queue()
```

# Development
## Setup
Clone this repository:
```console
git clone https://github.com/BlockScience/koi-net
```
Set up and activate virtual environment:
```shell
python -m venv venv
```
Windows:
```shell
.\venv\Scripts\activate
```
Linux:
```shell
source venv/bin/activate
```
Install koi-net with dev dependencies:
```shell
pip install -e .[dev]
```
## Distribution
*Be careful! All files not in `.gitignore` will be included in the distribution, even if they aren't tracked by git! Double check the `.tar.gz` after building to make sure you didn't accidently include other files.*

Build package:
```shell
python -m build
```
Push new package build to PyPI:
```shell
python -m twine upload --skip-existing dist/*
```