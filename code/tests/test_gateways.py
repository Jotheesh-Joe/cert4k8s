import logging
import unittest

from cert4k8s.config import Cert4K8sConfig
from cert4k8s.gateways import GatewayEventParser, GatewayParseError


def gateway_event(servers, annotations=None):
    return {
        "type": "ADDED",
        "object": {
            "metadata": {
                "name": "checkout",
                "namespace": "shop",
                "resourceVersion": "42",
                "annotations": annotations
                if annotations is not None
                else {
                    "jotheesh-joe.biz/cert4k8s": "enabled",
                    "jotheesh-joe.biz/cert4k8s-type": "dedicated",
                },
            },
            "spec": {
                "servers": servers,
            },
        },
    }


class GatewayEventParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = GatewayEventParser(
            config=Cert4K8sConfig(
                supported_domains=("dev.example.com", "staging.example.com"),
            ),
            logger=logging.getLogger("tests.gateways"),
        )

    def test_annotation_filter_requires_expected_values(self):
        event = gateway_event(
            servers=[],
            annotations={"jotheesh-joe.biz/cert4k8s": "disabled"},
        )

        self.assertFalse(self.parser.has_required_annotations(event))

    def test_parse_filters_supported_domains_per_server_without_leaking_hosts(self):
        event = gateway_event(
            servers=[
                {
                    "port": {"protocol": "HTTPS"},
                    "hosts": ["api.dev.example.com", "api.unsupported.test"],
                    "tls": {"credentialName": "api-tls"},
                },
                {
                    "port": {"protocol": "TLS"},
                    "hosts": ["web.staging.example.com"],
                    "tls": {"credentialName": "web-tls"},
                },
            ]
        )

        parsed = self.parser.parse(event)

        self.assertEqual(len(parsed.servers), 2)
        self.assertEqual(parsed.servers[0].hostnames, ("api.dev.example.com",))
        self.assertEqual(parsed.servers[1].hostnames, ("web.staging.example.com",))
        self.assertEqual(parsed.servers[0].secret_name, "api-tls")
        self.assertEqual(parsed.servers[1].secret_name, "web-tls")

    def test_parse_ignores_unsupported_protocols(self):
        event = gateway_event(
            servers=[
                {
                    "port": {"protocol": "HTTP"},
                    "hosts": ["api.dev.example.com"],
                }
            ]
        )

        parsed = self.parser.parse(event)

        self.assertEqual(parsed.servers, ())

    def test_parse_requires_tls_credential_for_supported_hosts(self):
        event = gateway_event(
            servers=[
                {
                    "port": {"protocol": "HTTPS"},
                    "hosts": ["api.dev.example.com"],
                    "tls": {},
                }
            ]
        )

        with self.assertRaises(GatewayParseError):
            self.parser.parse(event)


if __name__ == "__main__":
    unittest.main()
