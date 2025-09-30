"""Proxy-related helpers."""

from __future__ import annotations

import logging
import re
from typing import Final

import requests
from requests import Response
from requests.exceptions import HTTPError, InvalidSchema, ProxyError, RequestException

logger = logging.getLogger(__name__)


class ProxyValidationError(RuntimeError):
    """Raised when the configured proxy is missing or unreachable."""


class ProxyFormatError(ValueError):
    """Raised when a proxy URL cannot be parsed or normalised."""


_DEFAULT_TIMEOUT_S: Final[int] = 10
_FALLBACK_TEST_URLS: Final[tuple[str, ...]] = (
    "https://www.google.com/generate_204",
    "http://example.com/",
)
_SUPPORTED_PROXY_SCHEMES: Final[frozenset[str]] = frozenset(
    {"http", "https", "socks5", "socks5h", "socks4"}
)


def ensure_proxy_connectivity(
    proxy_url: str,
    test_url: str,
    *,
    timeout_s: int | None = None,
) -> None:
    """Verify that a proxy can reach at least one validation URL.

    The primary check targets ``test_url`` but we retry against a set of
    lightweight fallback URLs because some residential or rotating proxies block
    specific domains. Validation succeeds as soon as any probe succeeds.

    Raises:
        ProxyValidationError: if the proxy is absent, unreachable, or no test URL
            can be reached through it.
    """

    if not proxy_url:
        raise ProxyValidationError(
            "Proxy URL is empty. Set GMX_PROXY_URL or provide --proxy."
        )

    timeout = timeout_s or _DEFAULT_TIMEOUT_S
    proxies = {"http": proxy_url, "https": proxy_url}

    candidate_urls: tuple[str, ...] = (
        test_url,
        *tuple(url for url in _FALLBACK_TEST_URLS if url != test_url),
    )
    errors: list[str] = []

    for url in candidate_urls:
        logger.debug(
            "Validating proxy %s with timeout=%ss against %s", proxy_url, timeout, url
        )
        try:
            _probe_proxy(proxy_url, proxies, url, timeout)
            logger.debug("Proxy %s validated successfully via %s", proxy_url, url)
            return
        except ProxyValidationError as exc:
            logger.debug("Proxy validation against %s failed: %s", url, exc)
            errors.append(f"{url} -> {exc}")

    raise ProxyValidationError(
        "Proxy validation failed for all probe URLs. Last errors were:\n"
        + "\n".join(errors)
        + "\nIf your proxy uses SOCKS or another protocol, prefix it with the correct scheme (e.g. socks5://)."
    )


def _probe_proxy(
    proxy_url: str,
    proxies: dict[str, str],
    url: str,
    timeout: int,
) -> None:
    try:
        response: Response = requests.get(
            url,
            proxies=proxies,
            timeout=timeout,
            allow_redirects=True,
        )
    except ProxyError as exc:
        raise ProxyValidationError(
            f"Proxy {proxy_url} is unreachable or refused the connection"
        ) from exc
    except InvalidSchema as exc:
        raise ProxyValidationError(
            "Requests library is missing SOCKS support. Install the 'PySocks' package to enable schemes like socks5."
        ) from exc
    except RequestException as exc:
        raise ProxyValidationError(
            f"Failed to reach {url} through proxy {proxy_url}: {exc}"
        ) from exc

    try:
        response.raise_for_status()
    except HTTPError as exc:
        raise ProxyValidationError(
            f"Proxy returned status {response.status_code} for {url}"
        ) from exc
    finally:
        response.close()


_CREDENTIAL_PROXY_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<host>[^:]+):(?P<port>\d+):(?P<user>[^:]+):(?P<password>[^:]+)$"
)


def normalise_proxy_url(raw_proxy: str, *, default_scheme: str = "http") -> str:
    """Convert shorthand proxy notation to a full URL understood by Selenium.

    Supports inputs like ``host:port:user:pass`` or ``host:port`` and applies the
    provided ``default_scheme`` when the string is missing a scheme.
    """

    if not raw_proxy:
        return raw_proxy

    raw_proxy = raw_proxy.strip()

    if "://" in raw_proxy:
        scheme = raw_proxy.split("://", 1)[0].lower()
        if scheme not in _SUPPORTED_PROXY_SCHEMES:
            raise ProxyFormatError(
                f"Unsupported proxy scheme '{scheme}'. Supported schemes: {', '.join(sorted(_SUPPORTED_PROXY_SCHEMES))}."
            )
        return raw_proxy

    scheme = (default_scheme or "http").strip().lower()
    if scheme not in _SUPPORTED_PROXY_SCHEMES:
        raise ProxyFormatError(
            f"Unsupported proxy scheme '{scheme}'. Supported schemes: {', '.join(sorted(_SUPPORTED_PROXY_SCHEMES))}."
        )

    credential_match = _CREDENTIAL_PROXY_RE.match(raw_proxy)
    if credential_match:
        parts = credential_match.groupdict()
        return (
            f"{scheme}://{parts['user']}:{parts['password']}@"
            f"{parts['host']}:{parts['port']}"
        )

    host_port = raw_proxy.split(":")
    if len(host_port) == 2 and host_port[1].isdigit():
        return f"{scheme}://{raw_proxy}"

    raise ProxyFormatError(
        "Proxy must be in format host:port or host:port:user:password, or include scheme explicitly."
    )
