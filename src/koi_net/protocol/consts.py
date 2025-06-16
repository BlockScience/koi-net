"""API paths for KOI-net protocol."""

BROADCAST_EVENTS_PATH = "/events/broadcast"
POLL_EVENTS_PATH      = "/events/poll"
FETCH_RIDS_PATH       = "/rids/fetch"
FETCH_MANIFESTS_PATH  = "/manifests/fetch"
FETCH_BUNDLES_PATH    = "/bundles/fetch"

"""Headers for secure KOI-net protocol."""

KOI_NET_MESSAGE_SIGNATURE = "KOI-Net-Message-Signature"
KOI_NET_SOURCE_NODE_RID = "KOI-Net-Source-Node-RID"
KOI_NET_TARGET_NODE_RID = "KOI-Net-Target-Node-RID"
KOI_NET_TIMESTAMP = "KOI-Net-Timestamp"