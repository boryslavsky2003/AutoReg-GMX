"""Factories for building configured Selenium WebDriver instances."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

from .config import SeleniumConfig


def _find_chrome_binary() -> str | None:
    if binary := os.getenv("CHROME_BINARY"):
        return binary

    linux_candidates = (
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    )
    for candidate in linux_candidates:
        if Path(candidate).is_file():
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

    if binary := _find_chrome_binary():
        options.binary_location = binary

    if config.proxy_url:
        options.add_argument(f"--proxy-server={config.proxy_url}")
        options.add_argument("--proxy-bypass-list=<-loopback>")

    prefs = {
        "download.default_directory": str(config.downloads_dir),
        "download.prompt_for_download": False,
    }
    options.add_experimental_option("prefs", prefs)

    return options


def build_driver(config: SeleniumConfig) -> WebDriver:
    """Instantiate and configure a Chrome WebDriver instance."""

    options = _build_chrome_options(config)
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options,
    )
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
