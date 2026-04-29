"""Istio Gateway watch-event parsing."""

import logging
from typing import Dict, Optional, Tuple

from cert4k8s.config import Cert4K8sConfig
from cert4k8s.models import GatewayEvent, GatewayServer


class GatewayParseError(ValueError):
    """Raised when a Gateway event cannot be safely interpreted."""


class GatewayEventParser:
    """Convert raw Kubernetes watch events into cert4k8s Gateway events."""

    def __init__(
        self,
        config: Cert4K8sConfig,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._config = config
        self._logger = logger or logging.getLogger(__name__)

    def has_required_annotations(self, raw_event: Dict[str, object]) -> bool:
        """Return whether the Gateway has the required cert4k8s annotations."""
        annotations = self._annotations(raw_event)
        return all(
            annotations.get(key) == value
            for key, value in self._config.required_annotations
        )

    def gateway_name(self, raw_event: Dict[str, object]) -> str:
        """Return the Gateway name if present, otherwise unknown."""
        metadata = self._metadata(raw_event)
        return str(metadata.get("name") or "unknown")

    def parse(self, raw_event: Dict[str, object]) -> GatewayEvent:
        """Parse a raw Kubernetes Gateway watch event."""
        event_type = raw_event.get("type")
        if not isinstance(event_type, str) or not event_type:
            raise GatewayParseError("Gateway watch event is missing type")

        gateway_object = raw_event.get("object")
        if not isinstance(gateway_object, dict):
            raise GatewayParseError("Gateway watch event is missing object")

        metadata = gateway_object.get("metadata")
        if not isinstance(metadata, dict):
            raise GatewayParseError("Gateway object is missing metadata")

        name = self._required_string(metadata, "name")
        namespace = self._required_string(metadata, "namespace")

        spec = gateway_object.get("spec")
        if not isinstance(spec, dict):
            raise GatewayParseError("Gateway %s is missing spec" % name)

        servers_payload = spec.get("servers")
        if not isinstance(servers_payload, list):
            raise GatewayParseError("Gateway %s has no server list" % name)

        servers = []
        for server_payload in servers_payload:
            if not isinstance(server_payload, dict):
                raise GatewayParseError("Gateway %s contains an invalid server" % name)

            parsed_server = self._parse_server(name, server_payload)
            if parsed_server is not None:
                servers.append(parsed_server)

        return GatewayEvent(
            event_type=event_type,
            name=name,
            namespace=namespace,
            servers=tuple(servers),
        )

    def _parse_server(
        self,
        gateway_name: str,
        server_payload: Dict[str, object],
    ) -> Optional[GatewayServer]:
        port = server_payload.get("port")
        if not isinstance(port, dict):
            raise GatewayParseError("Gateway %s server is missing port" % gateway_name)

        protocol = port.get("protocol")
        if protocol not in self._config.supported_protocols:
            self._logger.info("The Protocol mentioned in the Gateway is not supported")
            return None

        hosts_payload = server_payload.get("hosts")
        if not isinstance(hosts_payload, list):
            raise GatewayParseError("Gateway %s server is missing hosts" % gateway_name)

        hostnames = self._supported_hostnames(hosts_payload)
        if not hostnames:
            return None

        tls = server_payload.get("tls")
        if not isinstance(tls, dict):
            raise GatewayParseError(
                "Gateway %s server with supported hosts is missing tls" % gateway_name
            )

        secret_name = tls.get("credentialName")
        if not isinstance(secret_name, str) or not secret_name:
            raise GatewayParseError(
                "Gateway %s server with supported hosts is missing tls credentialName"
                % gateway_name
            )

        return GatewayServer(hostnames=hostnames, secret_name=secret_name)

    def _supported_hostnames(self, hosts_payload: list) -> Tuple[str, ...]:
        hostnames = []
        for hostname in hosts_payload:
            if not isinstance(hostname, str) or not hostname:
                raise GatewayParseError("Gateway server contains an invalid hostname")

            if hostname.endswith(self._config.supported_domains):
                hostnames.append(hostname)
            else:
                self._logger.info("%s the domain is not supported", hostname)

        return tuple(hostnames)

    @staticmethod
    def _required_string(payload: Dict[str, object], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise GatewayParseError("Gateway object is missing %s" % key)
        return value

    @staticmethod
    def _metadata(raw_event: Dict[str, object]) -> Dict[str, object]:
        gateway_object = raw_event.get("object")
        if not isinstance(gateway_object, dict):
            return {}
        metadata = gateway_object.get("metadata")
        if not isinstance(metadata, dict):
            return {}
        return metadata

    @classmethod
    def _annotations(cls, raw_event: Dict[str, object]) -> Dict[str, str]:
        annotations = cls._metadata(raw_event).get("annotations")
        if not isinstance(annotations, dict):
            return {}
        return annotations
