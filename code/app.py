"""Runtime entrypoint for cert4k8s."""

import logging
import sys

from kubernetes import client as kubernetes_client
from kubernetes import config as kubernetes_config
from kubernetes import watch as kubernetes_watch
from urllib3 import exceptions as urllib3_exceptions

from cert4k8s.certificates import CertificateManager
from cert4k8s.config import Cert4K8sConfig, ConfigError
from cert4k8s.controller import Cert4K8sController
from cert4k8s.gateways import GatewayEventParser
from cert4k8s.kubernetes_client import KubernetesResourceClient
from cert4k8s.logging_utils import configure_logging


def build_controller(logger: logging.Logger) -> Cert4K8sController:
    """Create the controller and its Kubernetes-backed dependencies."""
    app_config = Cert4K8sConfig.from_env()

    kubernetes_config.incluster_config.load_incluster_config()
    resource_client = KubernetesResourceClient(
        custom_objects_api=kubernetes_client.CustomObjectsApi(),
        watcher=kubernetes_watch.Watch(),
    )
    certificate_manager = CertificateManager(
        resource_client=resource_client,
        config=app_config,
        logger=logger,
    )
    gateway_parser = GatewayEventParser(config=app_config, logger=logger)

    return Cert4K8sController(
        config=app_config,
        resource_client=resource_client,
        certificate_manager=certificate_manager,
        gateway_parser=gateway_parser,
        logger=logger,
        api_exception_types=(kubernetes_client.exceptions.ApiException,),
        protocol_error_types=(urllib3_exceptions.ProtocolError,),
    )


def main() -> None:
    """Start cert4k8s."""
    configure_logging()
    logger = logging.getLogger("cert4k8s")

    try:
        controller = build_controller(logger)
        controller.run()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Something went wrong- please check logs %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
