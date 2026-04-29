"""cert4k8s controller orchestration."""

import logging
from typing import Optional, Tuple, Type

from cert4k8s.certificates import CertificateManager, CertificateOperationError
from cert4k8s.config import Cert4K8sConfig
from cert4k8s.gateways import GatewayEventParser, GatewayParseError
from cert4k8s.models import GatewayEvent


class Cert4K8sController:
    """Watch Istio Gateways and reconcile cert-manager Certificates."""

    def __init__(
        self,
        config: Cert4K8sConfig,
        resource_client,
        certificate_manager: CertificateManager,
        gateway_parser: GatewayEventParser,
        logger: Optional[logging.Logger] = None,
        api_exception_types: Tuple[Type[BaseException], ...] = (),
        protocol_error_types: Tuple[Type[BaseException], ...] = (),
    ) -> None:
        self._config = config
        self._client = resource_client
        self._certificates = certificate_manager
        self._gateway_parser = gateway_parser
        self._logger = logger or logging.getLogger(__name__)
        self._api_exception_types = api_exception_types
        self._protocol_error_types = protocol_error_types

    def run(self) -> None:
        """Run the Gateway watch loop."""
        self._logger.info("Starting cert4k8s")
        self._logger.info("Successfully started cert4k8s")
        self._logger.info("checking for istio gateways in the cluster")
        self._logger.info(
            "The following domains are supported by cert4k8s in this cluster are : %s",
            self._config.supported_domains,
        )
        self._logger.info("Trying to create wildcard certificate")
        self._certificates.create_wildcard_certificates(self._config.supported_domains)

        resource_version = None
        cycle = 0
        while True:
            try:
                if cycle >= self._config.max_watch_cycles:
                    self._logger.info("closing the cycle")
                    raise SystemExit(1)

                cycle += 1
                self._logger.info("cycle - %s", cycle)
                self._logger.info("watching for new gateway resource...")
                resource_version = self._watch_once(resource_version)
                self._logger.info("resetting connection with kube api server")
            except Exception as exc:
                if self._is_protocol_error(exc):
                    self._logger.info("resetting connection with kube api server")
                    continue
                if self._is_api_exception(exc):
                    self._logger.info("Resource version is too old. %s", exc)
                    resource_version = self._resource_version_from_error(exc)
                    continue

                self._logger.error(
                    "something went wrong with connection to kube api server. "
                    "Restarting the pod. Error message - %s%s",
                    exc,
                    type(exc),
                )
                break

    def _watch_once(self, resource_version: Optional[str]) -> Optional[str]:
        current_resource_version = resource_version
        for raw_event in self._client.stream_gateways(
            resource_version=resource_version,
            timeout_seconds=self._config.watch_timeout_seconds,
        ):
            current_resource_version = self._resource_version(raw_event)
            self._handle_raw_event(raw_event)
        return current_resource_version

    def _handle_raw_event(self, raw_event: dict) -> None:
        try:
            if not self._gateway_parser.has_required_annotations(raw_event):
                self._logger.info(
                    "Required annotations are not present, so the gateway - %s is ignored",
                    self._gateway_parser.gateway_name(raw_event),
                )
                return

            gateway_event = self._gateway_parser.parse(raw_event)
            if gateway_event.event_type == "ADDED":
                self._handle_added(gateway_event)
            elif gateway_event.event_type == "DELETED":
                self._handle_deleted(gateway_event)
            elif gateway_event.event_type == "MODIFIED":
                self._handle_modified(gateway_event)
            else:
                self._logger.info("Gateway event type %s is ignored", gateway_event.event_type)
        except GatewayParseError as exc:
            self._logger.error("%s", exc)
        except CertificateOperationError as exc:
            self._logger.error("%s", exc)
        except Exception as exc:
            self._logger.error("%s", exc)

    def _handle_added(self, gateway_event: GatewayEvent) -> None:
        self._logger.info("%s", gateway_event.as_legacy_added_dicts())
        if not gateway_event.servers:
            self._logger.info(
                "%s contains a domain which is not supported or the protocol is not supported",
                gateway_event.as_legacy_added_dicts(),
            )
            return

        for server_index, server in enumerate(gateway_event.servers, start=1):
            self._certificates.create_for_gateway_server(gateway_event, server, server_index)

    def _handle_deleted(self, gateway_event: GatewayEvent) -> None:
        self._logger.info("%s", gateway_event.as_legacy_event_dict())
        if not gateway_event.servers:
            self._logger.info(
                "%s contains a domain which is not supported",
                gateway_event.as_legacy_event_dict(),
            )
            return

        self._certificates.delete_for_gateway(gateway_event)

    def _handle_modified(self, gateway_event: GatewayEvent) -> None:
        self._logger.info("%s", gateway_event.as_legacy_event_dict())
        if not gateway_event.servers:
            self._logger.info(
                "%s contains a domain which is not supported",
                gateway_event.as_legacy_event_dict(),
            )
            return

        gateway_names = self._certificates.list_gateway_names(gateway_event.namespace)
        if gateway_event.name not in gateway_names:
            self._logger.info("%s- gateway is deleted", gateway_event.name)
            self._logger.info("trying to delete the certificate created for the gateway")
            self._certificates.delete_for_gateway(gateway_event)
            return

        inventory = self._certificates.list_inventory()
        for server_index, server in enumerate(gateway_event.servers, start=1):
            certificate_name = gateway_event.certificate_name(server_index)
            if certificate_name in inventory.certificate_names:
                self._logger.info("certificate already present for the gateway")
                self._logger.info("Certificate found - so try to patch it")
                certificate_details = self._certificates.get_certificate_details(
                    certificate_name
                )
                if certificate_details.matches_server(server):
                    self._logger.info(
                        "no modification to dns and secret so patching is not needed"
                    )
                else:
                    self._certificates.patch_for_gateway_server(
                        gateway_event,
                        server,
                        server_index,
                    )
            else:
                self._logger.info("Certificate not found - so try to create it")
                self._certificates.create_for_gateway_server(
                    gateway_event,
                    server,
                    server_index,
                )

    def _is_protocol_error(self, exc: BaseException) -> bool:
        return bool(self._protocol_error_types) and isinstance(
            exc,
            self._protocol_error_types,
        )

    def _is_api_exception(self, exc: BaseException) -> bool:
        return bool(self._api_exception_types) and isinstance(
            exc,
            self._api_exception_types,
        )

    @staticmethod
    def _resource_version(raw_event: dict) -> Optional[str]:
        gateway_object = raw_event.get("object")
        if not isinstance(gateway_object, dict):
            return None
        metadata = gateway_object.get("metadata")
        if not isinstance(metadata, dict):
            return None
        resource_version = metadata.get("resourceVersion")
        if not isinstance(resource_version, str):
            return None
        return resource_version

    @staticmethod
    def _resource_version_from_error(exc: BaseException) -> Optional[str]:
        words = str(exc).split()
        if not words:
            return None
        return words[-1].strip("()'\"")
