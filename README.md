# KOI-net

*This specification is the result of several iterations of KOI research, [read more here](https://github.com/BlockScience/koi).*

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

This means that events are essentially just an RID, manifest, or bundle with an event type attached. Event types can be one of `FORGET`, `UPDATE`, or `NEW` forming the "FUN" acronym. While these types roughly correspond to delete, update, and create from CRUD operations, but they are not commands, they are signals. A node emits an event to indicate that its internal state has changed:
- `NEW` - indicates an previously unknown RID was cached
- `UPDATE` - indicates a previously known RID was cached
- `FORGET` - indicates a previously known RID was deleted

Nodes may broadcast events to other nodes to indicate their internal state changed. Conversely, nodes may also listen to events from other nodes and as a result decide to change their internal state, take some other action, or do nothing.


# Quickstart
## Setup

The bulk of the code in this repo is taken up by the Python reference implementation, which can be used in other projects to easily set up and configure your own KOI-net node.

This package can be installed with pip:
```
pip install koi-net
```

## Creating a Node

*Check out the `examples/` folder to follow along!*

All of the KOI-net functionality comes from the `NodeInterface` class which provides methods to interact with the protocol API, a local RID cache, a view of the network, and an internal processing pipeline. To create a new node, you will need to give it a name and a profile. The name will be used to generate its unique node RID, and the profile stores basic configuration data which will be shared with the other nodes that you communciate with.

Your first decision will be whether to setup a partial or full node:
- Partial nodes only need to indicate their type, and optionally the RID types of events they provide.
- Full nodes need to indicate their type, the base URL for their KOI-net API, and optionally the RID types of events and state they provide.

### Partial Node
```python
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeProvides, NodeType

node = NodeInterface(
    name="mypartialnode",
    profile=NodeProfile(
        node_type=NodeType.PARTIAL,
        provides=NodeProvides(
            event=[]
        )
    )
)
```
### Full Node
```python
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeProvides, NodeType

node = NodeInterface(
    name="myfullnode",
    profile=NodeProfile(
        base_url="http://127.0.0.1:8000",
        node_type=NodeType.FULL,
        provides=NodeProvides(
            event=[],
            state=[]
        )
    )
)
```

## Knowledge Processing

Next we'll set up the knowledge processing flow for our node. This is where most of the node's logic and behavior will come into play. For partial nodes this will be an event loop, and for full nodes we will use webhooks. Make sure to call `node.initialize()` and `node.finalize()` at the beginning and end of your node's life cycle.

### Partial Node
Make sure to set `source=KnowledgeSource.External`, this indicates to the knowledge processing pipeline that the incoming knowledge was received from an external source. Where the knowledge is sourced from will impact decisions in the node's knowledge handlers.
```python
import time
from koi_net.processor.knowledge_object import KnowledgeSource

if __name__ == "__main__":
    node.initialize()

    try:
        while True:
            for event in node.network.poll_neighbors():
                node.processor.handle(event=event, source=KnowledgeSource.External)
            node.processor.flush_kobj_queue()
            
            time.sleep(5)
            
    finally:
        node.finalize()
```

### Full Node
Setting up a full node is slightly more complex as we'll need a webserver. For this example, we'll use FastAPI and uvicorn. First we need to setup the "lifespan" of the server, to initialize and finalize the node before and after execution, as well as the FastAPI app which will be our web server.
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    node.initialize()
    yield
    node.finalize()


app = FastAPI(lifespan=lifespan, root_path="/koi-net")
```

Next we'll add our event handling webhook endpoint, which will allow other nodes to broadcast events to us. You'll notice that we have a similar loop to our partial node, but instead of polling periodicially, we handle events asynchronously as we receive them from other nodes.

```python
from koi_net.protocol.api_models import *
from koi_net.protocol.consts import *

@app.post(BROADCAST_EVENTS_PATH)
def broadcast_events(req: EventsPayload, background: BackgroundTasks):
    for event in req.events:
        node.processor.handle(event=event, source=KnowledgeSource.External)
    
    background.add_task(node.processor.flush_kobj_queue)
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
```
pip install .[examples]
```
Then you can start each node in a separate terminal:
```
python -m examples.basic_coordinator_node
```
```
python -m examples.basic_partial_node
```

# Implementation Reference
This section provides high level explanations of the Python implementation. More detailed explanations of methods can be found in the docstrings within the codebase itself.

## Node Interface
The node class mostly acts as a container for other classes with more specialized behavior, with special functions that should be called to start up and shut down a node. We'll take a look at each of these components in turn, but here is the class stub:
```python
class NodeInterface:
    cache: Cache
    identity: NodeIdentity
    network: NetworkInterface
    processor: ProcessorInterface
    first_contact: str

    def __init__(
        self, 
        name: str,
        profile: NodeProfile,
        identity_file_path: str = "identity.json",
        first_contact: str | None = None,
        handlers: list[KnowledgeHandler] | None = None,
        cache: Cache | None = None,
        network: NetworkInterface | None = None,
        processor: ProcessorInterface | None = None
    ): ...

    def initialize(self): ...
    def finalize(self): ...
```
As you can see, only a name and profile are required. The other fields allow for additional customization if needed.

## Node Identity
The `NodeIdentity` class provides easy access to a node's own RID, profile, and bundle. It provides access to the following properties after initialization, accessed with `node.identity`.
```python
class NodeIdentity:
    rid: KoiNetNode # an RID type
    profile: NodeProfile
    bundle: Bundle
```
This it what is initialized from the required `name` and `profile` fields in the `NodeInterface` constructor. Node RIDs take the form of `orn:koi-net.node:<name>+<uuid>`, and are generated on first use to the identity JSON file along with a the node profile.

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
    def flush_all_webhook_queues(self): ...

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
    def __init__(
        self, 
        cache: Cache, 
        network: NetworkInterface,
        identity: NodeIdentity,
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
        source: KnowledgeSource = KnowledgeSource.Internal,
        flush: bool = False
    ): ...
```

The `register_handler` method is a decorator which can wrap a function to create a new `KnowledgeHandler` and add it to the processing pipeline in a single step. The `add_handler` method adds an existing `KnowledgeHandler` to the processining pipeline.

The most commonly used functions in this class are `handle` and `flush_kobj_queue`. The `handle` method can be called on RIDs, manifests, bundles, and events to convert them to normalized to `KnowledgeObject` instances which are then added to the processing queue. The `flush` flag can be set to `True` to immediately start processing, or `flush_kobj_queue` can be called after queueing multiple knowledge objects. When calling the `handle` method, knowledge objects are marked as internally source by default. If you are handling RIDs, manifests, bundles, or events sourced from other nodes, `source` should be set to `KnowledgeSource.External`.

Here is an example of how an event polling loop would be implemented using the knowledge processing pipeline:
```python
for event in node.network.poll_neighbors():
    node.processor.handle(event=event, source=KnowledgeSource.External)
node.processor.flush_kobj_queue()
```