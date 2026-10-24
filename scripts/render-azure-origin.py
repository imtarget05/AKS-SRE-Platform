#!/usr/bin/env python3
"""Render the Azure public origin Gateway. This command never applies resources."""
from __future__ import annotations

import argparse
import re
import sys

import yaml

DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def valid_name(value: str) -> str:
    if not DNS_LABEL.fullmatch(value):
        raise argparse.ArgumentTypeError("must be an RFC 1123 DNS label (lowercase letters, digits, hyphens)")
    return value


def resources(resource_group: str, public_ip_name: str, dns_label: str,
              server_certificate_secret: str, client_ca_secret: str) -> list[dict]:
    if not resource_group or "<" in resource_group or ">" in resource_group:
        raise ValueError("Azure resource group is required and cannot be a placeholder")
    namespace = "platform-gateway"
    return [
        {
            "apiVersion": "gateway.envoyproxy.io/v1alpha1",
            "kind": "EnvoyProxy",
            "metadata": {"name": "portfolio-proxy-config", "namespace": namespace},
            "spec": {
                "provider": {
                    "type": "Kubernetes",
                    "kubernetes": {
                        "envoyService": {
                            "type": "LoadBalancer",
                            "annotations": {
                                "service.beta.kubernetes.io/azure-load-balancer-resource-group": resource_group,
                                "service.beta.kubernetes.io/azure-pip-name": public_ip_name,
                                "service.beta.kubernetes.io/azure-dns-label-name": dns_label,
                            },
                        },
                        "envoyDeployment": {
                            "replicas": 2,
                            "container": {
                                "resources": {
                                    "requests": {"cpu": "100m", "memory": "128Mi"},
                                    "limits": {"memory": "512Mi"},
                                }
                            },
                        },
                    },
                }
            },
        },
        {
            "apiVersion": "gateway.networking.k8s.io/v1",
            "kind": "Gateway",
            "metadata": {"name": "portfolio-gateway", "namespace": namespace},
            "spec": {
                "gatewayClassName": "portfolio-gatewayclass",
                "listeners": [{
                    "name": "https",
                    "protocol": "HTTPS",
                    "port": 443,
                    "tls": {
                        "mode": "Terminate",
                        "certificateRefs": [{"name": server_certificate_secret, "kind": "Secret"}],
                    },
                    "allowedRoutes": {
                        "namespaces": {
                            "from": "Selector",
                            "selector": {"matchLabels": {"portfolio.gateway/attach": "true"}},
                        }
                    },
                }],
            },
        },
        {
            "apiVersion": "gateway.envoyproxy.io/v1alpha1",
            "kind": "ClientTrafficPolicy",
            "metadata": {"name": "cloudflare-client-mtls", "namespace": namespace},
            "spec": {
                "targetRefs": [{
                    "group": "gateway.networking.k8s.io",
                    "kind": "Gateway",
                    "name": "portfolio-gateway",
                }],
                "tls": {
                    "clientValidation": {
                        "caCertificateRefs": [{"name": client_ca_secret, "kind": "Secret"}]
                    }
                },
            },
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--public-ip-name", required=True, type=valid_name)
    parser.add_argument("--dns-label", required=True, type=valid_name)
    parser.add_argument("--server-certificate-secret", required=True, type=valid_name)
    parser.add_argument("--client-ca-secret", required=True, type=valid_name)
    args = parser.parse_args()
    yaml.safe_dump_all(
        resources(args.resource_group, args.public_ip_name, args.dns_label,
                  args.server_certificate_secret, args.client_ca_secret),
        sys.stdout,
        sort_keys=False,
        explicit_start=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
