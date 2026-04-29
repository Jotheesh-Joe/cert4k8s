import unittest

from cert4k8s.config import Cert4K8sConfig, ConfigError


class Cert4K8sConfigTests(unittest.TestCase):
    def test_from_env_parses_and_deduplicates_supported_domains(self):
        config = Cert4K8sConfig.from_env(
            {"URLS": "dev.example.com, staging.example.com,dev.example.com"}
        )

        self.assertEqual(
            config.supported_domains,
            ("dev.example.com", "staging.example.com"),
        )

    def test_from_env_requires_urls(self):
        with self.assertRaises(ConfigError):
            Cert4K8sConfig.from_env({})

    def test_from_env_rejects_malformed_domains(self):
        with self.assertRaises(ConfigError):
            Cert4K8sConfig.from_env({"URLS": "*.example.com"})

        with self.assertRaises(ConfigError):
            Cert4K8sConfig.from_env({"URLS": "example"})


if __name__ == "__main__":
    unittest.main()
