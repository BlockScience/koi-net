# KOI-net

*This specification is the result of several iterations of KOI research, [read more here](https://github.com/BlockScience/koi).*

# Protocol
## Introduction

*This project builds upon and uses the [RID protocol](https://github.com/BlockScience/rid-lib) to identify and coordinate around knowledge objects.*

This protocol defines the standard communication patterns and coordination norms needed to establish and maintain Knowledge Organization Infrastructure (KOI) networks. KOI-nets are heterogenous compositions of KOI nodes, each of which is capable of autonomously inputting, processing, and outputting knowledge. The behavior of each node and configuration of each network can vary greatly, thus the protocol is designed to be a simple and flexible but interoperable foundation for future projects to build on. The protocol only governs communication between nodes, not how they operate internally. As a result we consider KOI-nets to be fractal-like, in that a network of nodes may act like a single node from an outside perspective.

Generated OpenAPI documentation is provided in this repository, and can be [viewed interactively with Swagger](https://generator.swagger.io/?url=https://raw.githubusercontent.com/BlockScience/koi/refs/heads/main/koi_v3_node_api.yaml).

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

Nodes may broadcast events to other nodes to indicate its internal state changed. Conversely, nodes may also listen to events from other nodes and decide to change their internal state, take some other action, or do nothing.


# Implementation
## Setup

The bulk of the code in this repo is taken up by the Python reference implementation, which can be used in other projects to easily set up and configure your own KOI node.

This package can be installed with pip:
```
pip install koi-net
```

## Node Interface
All of the KOI-net functionality comes from the `NodeInterface` class which provides methods to interact with the protocol API, a local RID cache, a view of the network, and an internal processing pipeline. To create a new node, you will need to give it a name and a profile. The name will be used to generate its unique node RID, and the profile stores basic configuration data which will be shared with other nodes you communciate with (it will be stored in the bundle associated with your node's RID). 
- Partial nodes only need to indicate their type, and optionally the RID types of events they provide.
- Full nodes need to indicate their type, the base URL for their KOI-net API, and optionally the RID types of events and state they provide.

```python
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeProvides, NodeType

# partial node configuration

partial_node = NodeInterface(
    name="mypartialnode",
    profile=NodeProfile(
        node_type=NodeType.PARTIAL,
        provides=NodeProvides(
            event=[]
        )
    )
)

# full node configuration

full_node = NodeInterface(
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
```
class NodeIdentity:
    rid: KoiNetNode # an RID type
    profile: NodeProfile
    bundle: Bundle
```
This it what is initialized from the required `name` and `profile` fields in the `NodeInterface` constructor.

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

    def get_state_providers(self, rid_type: RIDType): ...

    def fetch_remote_bundle(self, rid: RID): ...

    def fetch_remote_manifest(self, rid: RID): ...

    def poll_neighbors(self) -> list[Event]: ...

