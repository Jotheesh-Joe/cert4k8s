import logging
import unittest

from cert4k8s.certificates import CertificateManager
from cert4k8s.config import Cert4K8sConfig
from cert4k8s.models import GatewayEvent, GatewayServer


class FakeResourceClient:
    def __init__(self):
        self.certificates = []
        self.created = []
        self.patched = []
        self.deleted = []

    def list_certificates(self, namespace):
        return {"items": self.certificates}

    def create_certificate(self, namespace, body):
        self.created.append((namespace, body))
        self.certificates.append(
            {
                "metadata": {"name": body["metadata"]["name"]},
                "spec": {
                    "dnsNames": body["spec"]["dnsNames"],
                    "secretName": body["spec"]["secretName"],
                },
            }
        )
        return {"created": body["metadata"]["name"]}

    def patch_certificate(self, namespace, name, body):
        self.patched.append((namespace, name, body))
        return {"patched": name}

    def delete_certificate(self, namespace, name):
        self.deleted.append((namespace, name))
        return {"deleted": name}

    def get_certificate(self, namespace, name):
        for certificate in self.certificates:
            if certificate["metadata"]["name"] == name:
                return certificate
        raise KeyError(name)

    def list_gateways(self, namespace):
        return {"items": [{"metadata": {"name": "checkout"}}]}


class CertificateManagerTests(unittest.TestCase):
    def setUp(self):
        self.config = Cert4K8sConfig(
            supported_domains=("dev.example.com",),
        )
        self.client = FakeResourceClient()
        self.manager = CertificateManager(
            resource_client=self.client,
            config=self.config,
            logger=logging.getLogger("tests.certificates"),
            sleeper=lambda _seconds: None,
        )

    def test_build_certificate_body_preserves_spec_shape(self):
        body = self.manager.build_certificate_body(
            name="checkout-shop-cert-1",
            dns_names=("api.dev.example.com",),
            secret_name="checkout-tls",
        )

        self.assertEqual(body["apiVersion"], "cert-manager.io/v1")
        self.assertEqual(body["kind"], "Certificate")
        self.assertEqual(body["metadata"]["namespace"], "istio-system")
        self.assertEqual(body["metadata"]["labels"]["created-by"], "cert4k8s")
        self.assertEqual(body["spec"]["dnsNames"], ["api.dev.example.com"])
        self.assertEqual(body["spec"]["secretName"], "checkout-tls")
        self.assertEqual(
            body["spec"]["issuerRef"],
            {
                "group": "cert-manager.io",
                "kind": "ClusterIssuer",
                "name": "letsencrypt-dns01",
            },
        )

    def test_gateway_certificate_name_preserves_original_pattern(self):
        event = GatewayEvent(
            event_type="ADDED",
            name="checkout",
            namespace="shop",
            servers=(),
        )

        self.assertEqual(event.certificate_name(1), "checkout-shop-cert-1")

    def test_create_for_gateway_server_filters_existing_dns_names(self):
        self.client.certificates.append(
            {
                "metadata": {"name": "other-cert"},
                "spec": {
                    "dnsNames": ["api.dev.example.com"],
                    "secretName": "other-secret",
                },
            }
        )
        event = GatewayEvent(
            event_type="ADDED",
            name="checkout",
            namespace="shop",
            servers=(),
        )
        server = GatewayServer(
            hostnames=("api.dev.example.com", "web.dev.example.com"),
            secret_name="checkout-tls",
        )

        self.manager.create_for_gateway_server(event, server, 1)

        self.assertEqual(len(self.client.created), 1)
        self.assertEqual(
            self.client.created[0][1]["spec"]["dnsNames"],
            ["web.dev.example.com"],
        )

    def test_create_wildcard_certificate_uses_legacy_names(self):
        self.manager.create_wildcard_certificates(("dev.example.com",))

        self.assertEqual(len(self.client.created), 1)
        body = self.client.created[0][1]
        self.assertEqual(body["metadata"]["name"], "dev-example-com")
        self.assertEqual(body["spec"]["dnsNames"], ["*.dev.example.com"])
        self.assertEqual(body["spec"]["secretName"], "dev-example-wildcard-cert")


if __name__ == "__main__":
    unittest.main()
