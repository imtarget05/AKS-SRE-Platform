"""Offline controls for the live origin mTLS proof script."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "test-origin-mtls.sh"
FAKE_CURL = '''#!/usr/bin/env python3
import hashlib
import hmac
import os
import pathlib
import sys

args = sys.argv[1:]
url = next((arg for arg in args if arg.startswith("https://")), "")
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(url + "\\n")
body = pathlib.Path(args[args.index("-o") + 1]) if "-o" in args else None
headers = pathlib.Path(args[args.index("-D") + 1]) if "-D" in args else None
if "origin.example" in url:
    mode = os.environ["FAKE_NEG"]
    if mode == "alert":
        print("Connected to origin.example (127.0.0.1) port 443; tlsv13 alert certificate required", file=sys.stderr)
        print("000", end="")
        sys.exit(56)
    if mode == "dns":
        print("Could not resolve host: origin.example", file=sys.stderr)
        print("000", end="")
        sys.exit(6)
    print("SSL certificate problem: unable to get local issuer certificate", file=sys.stderr)
    print("000", end="")
    sys.exit(60)
if os.environ["FAKE_POS"] == "healthy":
    content = '{"status":"healthy"}'
    nonce_header = args[args.index("-H") + 1] if "-H" in args else ""
    nonce = nonce_header.split(": ", 1)[1] if ": " in nonce_header else ""
    target = "other.example" if os.environ.get("FAKE_TARGET") == "wrong" else "origin.example"
    msg = f"{nonce}\\n{target}\\n200\\n{hashlib.sha256(content.encode()).hexdigest()}".encode()
    proof = hmac.new(os.environ["EDGE_PROOF_KEY"].encode(), msg, hashlib.sha256).hexdigest()
    if os.environ.get("FAKE_PROOF") == "forged": proof = "0" * 64
    if body: body.write_text(content)
    if headers: headers.write_text(f"HTTP/2 200\\nCache-Control: private, no-store\\nX-Portfolio-Origin-Target: {target}\\nX-Portfolio-Proof-Nonce: {nonce}\\nX-Portfolio-Origin-Proof: {proof}\\n")
    print("200", end="")
else:
    if body: body.write_text('{"error":"OriginUnavailable"}')
    if headers: headers.write_text("HTTP/2 503\\nCache-Control: private, no-store\\n")
    print("503", end="")
'''


class OriginMtlsScriptTests(unittest.TestCase):
    def run_script(self, negative, positive, *, target="correct", proof="valid"):
        with tempfile.TemporaryDirectory(prefix="origin-mtls-test-") as directory:
            root = Path(directory)
            curl = root / "curl"
            curl.write_text(FAKE_CURL)
            curl.chmod(0o755)
            ca = root / "origin-ca.pem"
            ca.write_text("synthetic CA fixture")
            calls = root / "calls.txt"
            calls.write_text("")
            env = {
                **os.environ,
                "PATH": f"{root}:{os.environ['PATH']}",
                "CALL_LOG": str(calls),
                "FAKE_NEG": negative,
                "FAKE_POS": positive,
                "FAKE_TARGET": target,
                "FAKE_PROOF": proof,
                "EDGE_PROOF_KEY": "test-secret-longer-than-thirty-two-bytes",
            }
            result = subprocess.run(
                ["bash", str(SCRIPT), "origin.example",
                 "https://edge.example/flashsale/health/live", str(ca)],
                env=env, text=True, capture_output=True, timeout=10, check=False,
            )
            return result, calls.read_text().splitlines()

    def test_certificate_alert_then_healthy_worker_path_passes(self):
        result, calls = self.run_script("alert", "healthy")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertIn("edge.example/flashsale/health/live", calls[1])

    def test_dns_failure_is_not_mtls_rejection(self):
        result, _ = self.run_script("dns", "healthy")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_origin_ca_is_not_mtls_rejection(self):
        result, _ = self.run_script("bad_ca", "healthy")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_worker_error_fails_positive_control(self):
        result, calls = self.run_script("alert", "error")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(calls), 2)

    def test_arbitrary_healthy_https_without_valid_proof_fails(self):
        result, _ = self.run_script("alert", "healthy", proof="forged")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_valid_proof_for_wrong_origin_fails(self):
        result, _ = self.run_script("alert", "healthy", target="wrong")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
