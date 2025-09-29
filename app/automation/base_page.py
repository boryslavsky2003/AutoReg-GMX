"""Base Selenium page object helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

Locator = Tuple[str, str]


@dataclass(slots=True)
class BasePage:
    driver: WebDriver
    default_timeout: int = 15

    def wait_until_visible(
        self, locator: Locator, timeout: int | None = None
    ) -> WebElement:
        wait = WebDriverWait(self.driver, timeout or self.default_timeout)
        return wait.until(EC.visibility_of_element_located(locator))

    def wait_until_clickable(
        self, locator: Locator, timeout: int | None = None
    ) -> WebElement:
        wait = WebDriverWait(self.driver, timeout or self.default_timeout)
        return wait.until(EC.element_to_be_clickable(locator))

    def fill_field(self, locator: Locator, value: str, clear: bool = True) -> None:
        element = self.wait_until_visible(locator)
        if clear:
            element.clear()
        element.send_keys(value)

    def click(self, locator: Locator, timeout: int | None = None) -> None:
        element = self.wait_until_clickable(locator, timeout)
        element.click()
