"""Kubernetes CustomObjects API wrapper."""

from typing import Dict, Iterable, Optional


class KubernetesResourceClient:
    """Wrap Kubernetes custom object calls used by cert4k8s."""

    def __init__(self, custom_objects_api, watcher) -> None:
        self._api = custom_objects_api
        self._watcher = watcher

    def list_certificates(self, namespace: str) -> Dict[str, object]:
        """List cert-manager Certificate objects in a namespace."""
        return self._api.list_namespaced_custom_object(
            group="cert-manager.io",
            version="v1",
            plural="certificates",
            namespace=namespace,
        )

    def create_certificate(self, namespace: str, body: Dict[str, object]) -> Dict[str, object]:
        """Create a cert-manager Certificate object."""
        return self._api.create_namespaced_custom_object(
            group="cert-manager.io",
            version="v1",
            plural="certificates",
            namespace=namespace,
            body=body,
        )

    def patch_certificate(
        self,
        namespace: str,
        name: str,
        body: Dict[str, object],
    ) -> Dict[str, object]:
        """Patch a cert-manager Certificate object."""
        return self._api.patch_namespaced_custom_object(
            group="cert-manager.io",
            version="v1",
            plural="certificates",
            namespace=namespace,
            name=name,
            body=body,
        )

    def delete_certificate(self, namespace: str, name: str) -> Dict[str, object]:
        """Delete a cert-manager Certificate object."""
        return self._api.delete_namespaced_custom_object(
            group="cert-manager.io",
            version="v1",
            plural="certificates",
            namespace=namespace,
            name=name,
        )

    def get_certificate(self, namespace: str, name: str) -> Dict[str, object]:
        """Get a cert-manager Certificate object."""
        return self._api.get_namespaced_custom_object(
            group="cert-manager.io",
            version="v1",
            plural="certificates",
            namespace=namespace,
            name=name,
        )

    def list_gateways(self, namespace: str) -> Dict[str, object]:
        """List Istio Gateway objects in a namespace."""
        return self._api.list_namespaced_custom_object(
            group="networking.istio.io",
            version="v1beta1",
            plural="gateways",
            namespace=namespace,
        )

    def stream_gateways(
        self,
        resource_version: Optional[str],
        timeout_seconds: int,
    ) -> Iterable[Dict[str, object]]:
        """Stream cluster-wide Istio Gateway watch events."""
        return self._watcher.stream(
            func=self._api.list_cluster_custom_object,
            group="networking.istio.io",
            version="v1beta1",
            plural="gateways",
            resource_version=resource_version,
            timeout_seconds=timeout_seconds,
        )
