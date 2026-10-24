from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "render-azure-origin.py"
spec = spec_from_file_location("azure_origin", path)
module = module_from_spec(spec)
spec.loader.exec_module(module)


class AzureOriginTests(unittest.TestCase):
    def test_https_origin_requires_client_certificate_and_static_ip(self):
        proxy, gateway, policy = module.resources(
            "aks-node-rg", "portfolio-origin-ip", "portfolio-origin-123",
            "origin-server-tls", "cloudflare-client-ca",
        )
        annotations = proxy["spec"]["provider"]["kubernetes"]["envoyService"]["annotations"]
        self.assertEqual(annotations["service.beta.kubernetes.io/azure-pip-name"], "portfolio-origin-ip")
        self.assertEqual(annotations["service.beta.kubernetes.io/azure-dns-label-name"], "portfolio-origin-123")
        self.assertEqual(gateway["spec"]["listeners"][0]["port"], 443)
        self.assertEqual(gateway["spec"]["listeners"][0]["protocol"], "HTTPS")
        self.assertEqual(gateway["spec"]["listeners"][0]["tls"]["certificateRefs"][0]["name"], "origin-server-tls")
        self.assertEqual(
            gateway["spec"]["listeners"][0]["allowedRoutes"]["namespaces"]["from"], "Selector"
        )
        self.assertEqual(
            policy["spec"]["tls"]["clientValidation"]["caCertificateRefs"][0]["name"],
            "cloudflare-client-ca",
        )

    def test_placeholders_are_rejected(self):
        with self.assertRaises(ValueError):
            module.resources("<node-rg>", "ip", "label", "server", "ca")
        with self.assertRaises(Exception):
            module.valid_name("REPLACE_ME")


if __name__ == "__main__":
    unittest.main()
