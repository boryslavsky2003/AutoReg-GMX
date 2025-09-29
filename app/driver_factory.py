"""Factories for building configured Selenium WebDriver instances."""

from __future__ import annotations

import logging
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


def _build_chrome_options(config: SeleniumConfig) -> Options:
    options = Options()
    options.add_argument(f"--window-size={config.window_width},{config.window_height}")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    if config.headless:
        options.add_argument("--headless=new")

    if config.proxy_url:
        options.add_argument(f"--proxy-server={config.proxy_url}")
        options.add_argument("--proxy-bypass-list=<-loopback>")

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


def build_driver(config: SeleniumConfig) -> WebDriver:
    options = _build_chrome_options(config)
    try:
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options,
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
    return driver


@contextmanager
def managed_driver(config: SeleniumConfig) -> Iterator[WebDriver]:
    driver = build_driver(config)
    try:
        yield driver
    finally:
        driver.quit()
