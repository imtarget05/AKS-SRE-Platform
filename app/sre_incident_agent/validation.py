"""Input validation for the SRE incident workflow adapters.

All functions fail closed: they raise ValueError on any input that does not
conform to the expected safe shape. Callers must validate before using values
in subprocess argv or URL query strings.
"""

from __future__ import annotations

import re
import urllib.parse

_DNS_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def validate_dns_label(value: str) -> str:
    """Validate an RFC 1123 DNS label.

    Lowercase alphanumeric plus hyphen, must start and end with alphanumeric,
    length 1-63. Rejects empty strings, double-hyphen, forward-slash,
    backslash, dot-dot, spaces, and any character outside [a-z0-9-].
    """
    if not isinstance(value, str):
        raise ValueError(f"dns label must be a string, got {type(value).__name__}")
    if not value:
        raise ValueError("dns label must not be empty")
    if len(value) > 63:
        raise ValueError(f"dns label too long ({len(value)} > 63): {value!r}")
    if "--" in value or "/" in value or "\\" in value or ".." in value or " " in value:
        raise ValueError(f"dns label contains forbidden sequence: {value!r}")
    if not _DNS_LABEL_RE.fullmatch(value):
        raise ValueError(f"dns label must match [a-z0-9]([a-z0-9-]*[a-z0-9])?: {value!r}")
    return value


def validate_namespace(namespace: str) -> str:
    """Validate namespace against the allowlist."""
    allowlist = {"monitoring", "flashsale", "kube-system"}
    if not isinstance(namespace, str):
        raise ValueError(f"namespace must be a string, got {type(namespace).__name__}")
    if namespace not in allowlist:
        raise ValueError(f"namespace not in allowlist {sorted(allowlist)}: {namespace!r}")
    return namespace


def ensure_double_dash(argv: list[str]) -> list[str]:
    """Ensure ``--`` appears right after the executable (index 1).

    Returns argv unchanged if ``--`` is already present.
    """
    if "--" in argv:
        return argv
    return [argv[0], "--", *argv[1:]]


def encode_promql(query: str) -> str:
    """URL-encode a PromQL query for safe use in a query string."""
    return urllib.parse.quote(query, safe="")
