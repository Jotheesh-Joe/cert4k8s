"""Internal data models for cert4k8s."""

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Tuple


@dataclass(frozen=True)
class GatewayServer:
    """A supported Gateway server section that needs certificate management."""

    hostnames: Tuple[str, ...]
    secret_name: str

    def as_legacy_dict(self) -> Dict[str, object]:
        """Return the dictionary shape used by the original procedural script."""
        return {
            "hostnames": list(self.hostnames),
            "secret_name": self.secret_name,
        }


@dataclass(frozen=True)
class GatewayEvent:
    """A parsed Kubernetes watch event for an Istio Gateway."""

    event_type: str
    name: str
    namespace: str
    servers: Tuple[GatewayServer, ...]

    def certificate_name(self, server_index: int) -> str:
        """Return the cert-manager Certificate name for a Gateway server."""
        return "%s-%s-cert-%s" % (self.name, self.namespace, server_index)

    def as_legacy_event_dict(self) -> Dict[str, object]:
        """Return a compact dictionary similar to the original log payload."""
        return {
            "Event": self.event_type,
            "Name": self.name,
            "Namespace": self.namespace,
            "servers": [server.as_legacy_dict() for server in self.servers],
        }

    def as_legacy_added_dicts(self) -> List[Dict[str, object]]:
        """Return original-style per-server event dictionaries."""
        base = {
            "Event": self.event_type,
            "Name": self.name,
            "Namespace": self.namespace,
        }
        return [
            dict(base, **server.as_legacy_dict())
            for server in self.servers
        ]


@dataclass(frozen=True)
class CertificateDetails:
    """The certificate fields cert4k8s compares before patching."""

    hostnames: Tuple[str, ...]
    secret_name: str

    def matches_server(self, server: GatewayServer) -> bool:
        """Return whether a certificate already matches a Gateway server."""
        return self.hostnames == server.hostnames and self.secret_name == server.secret_name


@dataclass(frozen=True)
class CertificateInventory:
    """A snapshot of existing cert-manager Certificates."""

    certificate_names: FrozenSet[str]
    dns_names: FrozenSet[str]
