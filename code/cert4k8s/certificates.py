"""Certificate management logic."""

import logging
import time
from typing import Callable, Dict, Iterable, Optional, Tuple

from cert4k8s.config import Cert4K8sConfig
from cert4k8s.models import (
    CertificateDetails,
    CertificateInventory,
    GatewayEvent,
    GatewayServer,
)


class CertificateOperationError(RuntimeError):
    """Raised when certificate state cannot be safely read or changed."""


class CertificateManager:
    """Create, patch, delete, and inspect cert-manager Certificate objects."""

    def __init__(
        self,
        resource_client,
        config: Cert4K8sConfig,
        logger: Optional[logging.Logger] = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = resource_client
        self._config = config
        self._logger = logger or logging.getLogger(__name__)
        self._sleep = sleeper

    def list_inventory(self) -> CertificateInventory:
        """Return existing Certificate names and DNS names."""
        try:
            response = self._client.list_certificates(self._config.certificate_namespace)
        except Exception as exc:
            message = (
                "Could not list the certificates in istio-system namespace : "
                "error message - %s" % exc
            )
            self._logger.error(message)
            raise CertificateOperationError(message) from exc

        certificate_names = set()
        dns_names = set()
        for item in response.get("items", []):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            name = metadata.get("name")
            if name:
                certificate_names.add(name)
            for dns_name in spec.get("dnsNames") or []:
                if dns_name:
                    dns_names.add(dns_name)

        return CertificateInventory(
            certificate_names=frozenset(certificate_names),
            dns_names=frozenset(dns_names),
        )

    def list_gateway_names(self, namespace: str) -> Tuple[str, ...]:
        """Return Gateway names from a namespace."""
        try:
            response = self._client.list_gateways(namespace)
        except Exception as exc:
            self._logger.error(
                "Could not list gateways in the namespace : error message - %s",
                exc,
            )
            raise

        names = []
        for item in response.get("items", []):
            name = (item.get("metadata") or {}).get("name")
            if name:
                names.append(name)
        return tuple(names)

    def create_wildcard_certificates(self, domains: Iterable[str]) -> None:
        """Create wildcard certificates for configured supported domains."""
        for domain in domains:
            inventory = self.list_inventory()
            certificate_name = domain.replace(".", "-")
            secret_name = self._wildcard_secret_name(domain)
            dns_name = "*.%s" % domain

            if (
                certificate_name in inventory.certificate_names
                or dns_name in inventory.dns_names
            ):
                self._logger.info(
                    "The wildcard certificate or dns is already in use, so no action will be taken"
                )
                self._logger.info(
                    "If new wildcard certificate is needed, delete the existing wildcard certificate and secret"
                )
                continue

            body = self.build_certificate_body(
                name=certificate_name,
                dns_names=(dns_name,),
                secret_name=secret_name,
            )
            self._create_certificate(body, self._config.wildcard_create_delay_seconds)
            self._logger.info("wild card certificate created")

    def create_for_gateway_server(
        self,
        gateway_event: GatewayEvent,
        server: GatewayServer,
        server_index: int,
    ) -> None:
        """Create a certificate for a Gateway server if needed."""
        certificate_name = gateway_event.certificate_name(server_index)
        inventory = self.list_inventory()

        if certificate_name in inventory.certificate_names:
            self._logger.info("certificate already present for the gateway")
            return

        new_dns_names = tuple(
            hostname for hostname in server.hostnames if hostname not in inventory.dns_names
        )
        if not new_dns_names:
            self._logger.info("hostname already present in a certificate")
            return

        skipped_dns_names = set(server.hostnames) - set(new_dns_names)
        for _hostname in skipped_dns_names:
            self._logger.info("hostname already present in a certificate")

        body = self.build_certificate_body(
            name=certificate_name,
            dns_names=new_dns_names,
            secret_name=server.secret_name,
        )
        self._create_certificate(body, self._config.create_delay_seconds)
        self._logger.info("certificate created")

    def patch_for_gateway_server(
        self,
        gateway_event: GatewayEvent,
        server: GatewayServer,
        server_index: int,
    ) -> None:
        """Patch a certificate to match a Gateway server."""
        certificate_name = gateway_event.certificate_name(server_index)
        body = self.build_certificate_body(
            name=certificate_name,
            dns_names=server.hostnames,
            secret_name=server.secret_name,
        )
        try:
            self._logger.info("trying to patch a cert")
            self._sleep(self._config.patch_delay_seconds)
            response = self._client.patch_certificate(
                namespace=self._config.certificate_namespace,
                name=certificate_name,
                body=body,
            )
            self._logger.info("%s", response)
            self._logger.info("certificate patched")
        except Exception as exc:
            self._logger.error(
                "Could not patch the certificate: error message - %s",
                exc,
            )

    def delete_for_gateway(self, gateway_event: GatewayEvent) -> None:
        """Delete certificates owned by a Gateway event."""
        for server_index, _server in enumerate(gateway_event.servers, start=1):
            certificate_name = gateway_event.certificate_name(server_index)
            try:
                response = self._client.delete_certificate(
                    namespace=self._config.certificate_namespace,
                    name=certificate_name,
                )
                self._logger.info("%s", response)
                self._logger.info("certificate deleted successfully")
            except Exception as exc:
                self._logger.error(
                    "could not delete the certificate: error message - %s",
                    exc,
                )

    def get_certificate_details(self, name: str) -> CertificateDetails:
        """Return DNS names and secret name for an existing Certificate."""
        try:
            response = self._client.get_certificate(
                namespace=self._config.certificate_namespace,
                name=name,
            )
        except Exception as exc:
            message = (
                "Could not find the certificate for the gateway server: "
                "error message - %s" % exc
            )
            self._logger.error(message)
            raise CertificateOperationError(message) from exc

        spec = response.get("spec") or {}
        return CertificateDetails(
            hostnames=tuple(spec.get("dnsNames") or ()),
            secret_name=spec.get("secretName") or "",
        )

    def build_certificate_body(
        self,
        name: str,
        dns_names: Iterable[str],
        secret_name: str,
    ) -> Dict[str, object]:
        """Build the cert-manager Certificate object body."""
        return {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Certificate",
            "metadata": {
                "name": name,
                "namespace": self._config.certificate_namespace,
                "labels": {
                    "created-by": self._config.created_by_label,
                },
            },
            "spec": {
                "dnsNames": list(dns_names),
                "issuerRef": {
                    "group": self._config.issuer_group,
                    "kind": self._config.issuer_kind,
                    "name": self._config.issuer_name,
                },
                "secretName": secret_name,
                "usages": ["digital signature", "key encipherment"],
            },
        }

    def _create_certificate(self, body: Dict[str, object], delay_seconds: int) -> None:
        try:
            self._logger.info("trying to create a cert")
            self._sleep(delay_seconds)
            response = self._client.create_certificate(
                namespace=self._config.certificate_namespace,
                body=body,
            )
            self._logger.info("%s", response)
        except Exception as exc:
            self._logger.error(
                "Could not create new certificate: error message - %s",
                exc,
            )

    @staticmethod
    def _wildcard_secret_name(domain: str) -> str:
        labels = domain.split(".")
        return "%s-%s-wildcard-cert" % (labels[0], labels[1])
