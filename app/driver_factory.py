"""Factories for building configured Selenium WebDriver instances."""

from __future__ import annotations

import logging
import sys
import traceback
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

from .config import SeleniumConfig

try:  # Optional dependency for advanced proxy handling (e.g., SOCKS with auth)
    import seleniumwire  # type: ignore
    from seleniumwire.webdriver import Chrome as WireChrome  # type: ignore

    _SELENIUM_WIRE_AVAILABLE = True
    _SELENIUM_WIRE_VERSION = getattr(seleniumwire, "__version__", "unknown")
except Exception as _wire_exc:  # pragma: no cover
    _SELENIUM_WIRE_AVAILABLE = False
    _SELENIUM_WIRE_VERSION = "unavailable"
    _SELENIUM_WIRE_IMPORT_ERROR = _wire_exc  # type: ignore[name-defined]
else:
    _SELENIUM_WIRE_IMPORT_ERROR = None  # type: ignore

# Alternative SOCKS handling via subprocess tunnel
import subprocess
import threading
import time
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ChromeBinaryNotFoundError(RuntimeError):
    """Raised when Chrome or Chromium executable cannot be located."""


def _find_chrome_binary() -> str | None:
    if binary := os.getenv("CHROME_BINARY"):
        logger.debug("Using Chrome binary from CHROME_BINARY=%s", binary)
        return binary

    linux_candidates = (
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    )
    for candidate in linux_candidates:
        if Path(candidate).is_file():
            logger.debug("Using Chrome binary at %s", candidate)
            return candidate
    return None


def _build_chrome_options(
    config: SeleniumConfig,
    *,
    attach_browser_proxy: bool,
) -> Options:
    options = Options()
    options.add_argument(f"--window-size={config.window_width},{config.window_height}")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    # SSL/Security bypasses for proxy compatibility
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-web-security")
    options.add_argument("--ignore-certificate-errors-spki-list")
    options.add_argument("--ignore-urlfetcher-cert-requests")

    if config.headless:
        options.add_argument("--headless=new")

    if attach_browser_proxy and config.proxy_url:
        options.add_argument(f"--proxy-server={config.proxy_url}")
        options.add_argument("--proxy-bypass-list=<-loopback>")
    elif not attach_browser_proxy and config.proxy_url:
        logger.debug(
            "Skipping direct --proxy-server injection for %s; will rely on selenium-wire",
            config.proxy_scheme,
        )

    prefs = {
        "download.default_directory": str(config.downloads_dir),
        "download.prompt_for_download": False,
    }
    options.add_experimental_option("prefs", prefs)

    binary = _find_chrome_binary()
    if binary:
        options.binary_location = binary
    else:
        logger.debug("Chrome binary not preset; Selenium will try system defaults")

    return options


def _create_local_http_tunnel_for_socks(socks_url: str) -> tuple[str, subprocess.Popen]:
    """Create local HTTP proxy that forwards to SOCKS proxy.
    Returns (local_http_url, process) tuple.
    """
    parsed = urlparse(socks_url)
    socks_host = parsed.hostname or "localhost"
    socks_port = parsed.port or 1080
    socks_user = parsed.username
    socks_pass = parsed.password

    # Find free local port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        local_port = s.getsockname()[1]

    # Use socat to create HTTP->SOCKS tunnel if available
    local_http_url = f"http://127.0.0.1:{local_port}"

    try:
        if socks_user and socks_pass:
            # For authenticated SOCKS, we'll use a simple Python bridge
            cmd = [
                "python",
                "-c",
                f"""
import socket, threading, select, sys
from urllib.parse import unquote
import socks

def handle_client(client_sock, socks_host, socks_port, socks_user, socks_pass):
    try:
        # Set up SOCKS connection
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, '{socks_host}', {socks_port}, username='{socks_user}', password='{socks_pass}')
        
        # Read HTTP CONNECT request
        request = client_sock.recv(4096).decode('utf-8')
        lines = request.split('\\r\\n')
        if lines[0].startswith('CONNECT '):
            target = lines[0].split()[1]
            host, port = target.split(':')
            s.connect((host, int(port)))
            client_sock.send(b'HTTP/1.1 200 Connection established\\r\\n\\r\\n')
            
            # Relay data
            def relay(src, dst):
                try:
                    while True:
                        data = src.recv(4096)
                        if not data: break
                        dst.send(data)
                except: pass
                finally:
                    src.close()
                    dst.close()
            
            t1 = threading.Thread(target=relay, args=(client_sock, s))
            t2 = threading.Thread(target=relay, args=(s, client_sock))
            t1.daemon = True
            t2.daemon = True
            t1.start()
            t2.start()
            t1.join()
            t2.join()
    except Exception as e:
        print(f'Tunnel error: {{e}}', file=sys.stderr)
    finally:
        try: client_sock.close()
        except: pass

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', {local_port}))
server.listen(5)

while True:
    client, addr = server.accept()
    t = threading.Thread(target=handle_client, args=(client, '{socks_host}', {socks_port}, '{socks_user}', '{socks_pass}'))
    t.daemon = True
    t.start()
""",
            ]
        else:
            # No auth - use socat if available, fallback to Python
            cmd = [
                "socat",
                f"TCP-LISTEN:{local_port},reuseaddr,fork",
                f"SOCKS4A:{socks_host}:{socks_port},socksport={socks_port}",
            ]

        logger.debug("Starting local HTTP->SOCKS tunnel: %s", " ".join(cmd[:3]))
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # Give tunnel time to start
        time.sleep(1)
        return local_http_url, proc

    except FileNotFoundError:
        # Fallback: return original SOCKS URL and let Chrome try directly
        logger.warning(
            "Could not create HTTP tunnel for SOCKS (missing socat/python). Chrome will try direct SOCKS connection."
        )
        return socks_url, None


def build_driver(config: SeleniumConfig) -> WebDriver:
    is_socks_proxy = bool(config.proxy_url) and config.proxy_scheme in {
        "socks5",
        "socks5h",
        "socks4",
    }

    use_selenium_wire = is_socks_proxy and _SELENIUM_WIRE_AVAILABLE
    use_local_tunnel = is_socks_proxy and not _SELENIUM_WIRE_AVAILABLE

    tunnel_process = None
    effective_proxy_url = config.proxy_url

    if use_local_tunnel and config.proxy_url:
        logger.info(
            "selenium-wire недоступний, створюю локальний HTTP тунель для SOCKS проксі"
        )
        effective_proxy_url, tunnel_process = _create_local_http_tunnel_for_socks(
            config.proxy_url
        )
        logger.info("Локальний тунель: %s -> %s", effective_proxy_url, config.proxy_url)

    options = _build_chrome_options(
        config,
        attach_browser_proxy=not use_selenium_wire,
    )

    # Override proxy URL for options if we created a tunnel
    if tunnel_process and effective_proxy_url != config.proxy_url:
        # Remove old proxy args and add new ones
        options._arguments = [
            arg for arg in options._arguments if not arg.startswith("--proxy-server")
        ]
        options.add_argument(f"--proxy-server={effective_proxy_url}")
        options.add_argument("--proxy-bypass-list=<-loopback>")

    if use_selenium_wire and not _SELENIUM_WIRE_AVAILABLE:
        # Provide rich diagnostics to help user see path mismatch / import issue.
        details_lines = [
            "selenium-wire недоступний для імпорту:",
            f"  Python exec: {sys.executable}",
            f"  sys.path (перші 5): {sys.path[:5]}",
            f"  _SELENIUM_WIRE_VERSION: {_SELENIUM_WIRE_VERSION}",
        ]
        if (
            "_SELENIUM_WIRE_IMPORT_ERROR" in globals()
            and _SELENIUM_WIRE_IMPORT_ERROR is not None
        ):  # type: ignore[name-defined]
            details_lines.append(
                "  Import exception: " + repr(_SELENIUM_WIRE_IMPORT_ERROR)  # type: ignore[name-defined]
            )
            tb = "".join(
                traceback.format_exception_only(
                    type(_SELENIUM_WIRE_IMPORT_ERROR), _SELENIUM_WIRE_IMPORT_ERROR
                )
            )  # type: ignore[name-defined]
            details_lines.append("  Exception type: " + tb.strip())
        logger.error("\n".join(details_lines))
        raise RuntimeError(
            "Налаштовано SOCKS проксі, але selenium-wire не імпортується. Перевірте, що пакет встановлено у ТОМУ Ж venv. "
            "Спробуйте: 'pip install --upgrade --force-reinstall selenium-wire PySocks' або запустіть './venv/bin/python -c \"import seleniumwire;print(1)\"'. "
            "Докладності записані у лог вище."
        )

    try:
        if use_selenium_wire:
            seleniumwire_options = {
                "proxy": {
                    # selenium-wire expects full schemes for upstream
                    "http": config.proxy_url,
                    "https": config.proxy_url,
                    "no_proxy": "localhost,127.0.0.1",
                },
                # keep request storage minimal to reduce memory
                "request_storage": {"max_entries": 50},
            }
            driver = WireChrome(  # type: ignore[assignment]
                service=ChromeService(ChromeDriverManager().install()),
                options=options,
                seleniumwire_options=seleniumwire_options,
            )
            logger.info(
                "Using selenium-wire with upstream proxy %s (scheme=%s)",
                config.proxy_url,
                config.proxy_scheme,
            )
        else:
            driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=options,
            )
            if use_local_tunnel:
                logger.info(
                    "Using local tunnel proxy %s for SOCKS %s (scheme=%s)",
                    effective_proxy_url,
                    config.proxy_url,
                    config.proxy_scheme,
                )
    except WebDriverException as exc:
        message = str(exc).lower()
        if "cannot find chrome binary" in message:
            raise ChromeBinaryNotFoundError(
                "Не знайдено виконуваний файл Google Chrome або Chromium. Встановіть браузер або задайте шлях у змінній CHROME_BINARY."
            ) from exc
        raise

    driver.implicitly_wait(config.implicit_wait_s)
    driver.set_page_load_timeout(config.page_load_timeout_s)

    # Store tunnel process for cleanup
    if tunnel_process:
        setattr(driver, "_tunnel_process", tunnel_process)

    return driver


@contextmanager
def managed_driver(config: SeleniumConfig) -> Iterator[WebDriver]:
    driver = build_driver(config)
    try:
        yield driver
    finally:
        # Clean up tunnel process if exists
        if hasattr(driver, "_tunnel_process") and driver._tunnel_process:
            try:
                driver._tunnel_process.terminate()
                driver._tunnel_process.wait(timeout=5)
                logger.debug("Закрито локальний проксі тунель")
            except Exception as e:
                logger.warning("Помилка при закритті тунелю: %s", e)

        driver.quit()
