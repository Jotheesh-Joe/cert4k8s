"""Application configuration and validation."""

import os
from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple


class ConfigError(ValueError):
    """Raised when cert4k8s runtime configuration is invalid."""


@dataclass(frozen=True)
class Cert4K8sConfig:
    """Validated runtime settings for cert4k8s."""

    supported_domains: Tuple[str, ...]
    certificate_namespace: str = "istio-system"
    issuer_group: str = "cert-manager.io"
    issuer_kind: str = "ClusterIssuer"
    issuer_name: str = "letsencrypt-dns01"
    created_by_label: str = "cert4k8s"
    create_delay_seconds: int = 120
    patch_delay_seconds: int = 90
    wildcard_create_delay_seconds: int = 10
    max_watch_cycles: int = 365
    watch_timeout_seconds: int = 240
    supported_protocols: Tuple[str, ...] = ("HTTPS", "TLS")
    required_annotations: Tuple[Tuple[str, str], ...] = field(
        default=(
            ("jotheesh-joe.biz/cert4k8s", "enabled"),
            ("jotheesh-joe.biz/cert4k8s-type", "dedicated"),
        )
    )

    @classmethod
    def from_env(cls, environ: Optional[Mapping[str, str]] = None) -> "Cert4K8sConfig":
        """Build configuration from environment variables."""
        env = environ if environ is not None else os.environ
        raw_urls = env.get("URLS")
        domains = cls.parse_supported_domains(raw_urls)
        return cls(supported_domains=domains)

    @staticmethod
    def parse_supported_domains(raw_urls: Optional[str]) -> Tuple[str, ...]:
        """Parse and validate the comma-separated URLS setting."""
        if raw_urls is None:
            raise ConfigError("URLS environment variable is required")

        cleaned_urls = raw_urls.replace(" ", "")
        raw_domains = [domain for domain in cleaned_urls.split(",") if domain]
        if not raw_domains:
            raise ConfigError("URLS environment variable must include at least one domain")

        domains = []
        seen = set()
        for domain in raw_domains:
            Cert4K8sConfig._validate_domain(domain)
            if domain not in seen:
                seen.add(domain)
                domains.append(domain)

        return tuple(domains)

    @staticmethod
    def _validate_domain(domain: str) -> None:
        if "/" in domain or "*" in domain:
            raise ConfigError("URLS entries must be domain suffixes, not paths or wildcards")
        if "." not in domain:
            raise ConfigError("URLS entries must be fully qualified domain suffixes")
        if domain.startswith(".") or domain.endswith(".") or ".." in domain:
            raise ConfigError("URLS contains a malformed domain: %s" % domain)

        labels = domain.split(".")
        for label in labels:
            if not label:
                raise ConfigError("URLS contains a malformed domain: %s" % domain)
            if label.startswith("-") or label.endswith("-"):
                raise ConfigError("URLS contains a malformed domain: %s" % domain)
            if not all(char.isalnum() or char == "-" for char in label):
                raise ConfigError("URLS contains a malformed domain: %s" % domain)
