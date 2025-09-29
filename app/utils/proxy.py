"""Proxy-related helpers."""

from __future__ import annotations

import logging
from typing import Final

import requests
from requests import Response
from requests.exceptions import HTTPError, ProxyError, RequestException

logger = logging.getLogger(__name__)


class ProxyValidationError(RuntimeError):
    """Raised when the configured proxy is missing or unreachable."""


_DEFAULT_TIMEOUT_S: Final[int] = 10


def ensure_proxy_connectivity(
    proxy_url: str,
    test_url: str,
    *,
    timeout_s: int | None = None,
) -> None:
    """Verify that a proxy can reach the desired test URL.

    Raises:
        ProxyValidationError: if the proxy is absent, unreachable, or the test URL
            cannot be reached through it.
    """

    if not proxy_url:
        raise ProxyValidationError(
            "Proxy URL is empty. Set GMX_PROXY_URL or provide --proxy."
        )

    timeout = timeout_s or _DEFAULT_TIMEOUT_S
    proxies = {"http": proxy_url, "https": proxy_url}

    logger.debug(
        "Validating proxy %s with timeout=%ss against %s", proxy_url, timeout, test_url
    )

    try:
        response: Response = requests.get(
            test_url,
            proxies=proxies,
            timeout=timeout,
            stream=True,
            allow_redirects=True,
        )
    except ProxyError as exc:
        raise ProxyValidationError(
            f"Proxy {proxy_url} is unreachable or refused the connection"
        ) from exc
    except RequestException as exc:
        raise ProxyValidationError(
            f"Failed to reach {test_url} through proxy {proxy_url}: {exc}"
        ) from exc

    try:
        response.raise_for_status()
    except HTTPError as exc:
        raise ProxyValidationError(
            f"Proxy returned status {response.status_code} for {test_url}"
        ) from exc
    finally:
        response.close()

    logger.debug("Proxy %s validated successfully", proxy_url)
