"""GMX specific page object for the signup form."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from ..data_models import RegistrationData
from .base_page import BasePage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GMXRegistrationLocators:
    FIRST_NAME: tuple[str, str] = (By.NAME, "firstName")
    LAST_NAME: tuple[str, str] = (By.NAME, "lastName")
    EMAIL_LOCAL_PART: tuple[str, str] = (By.NAME, "email")
    EMAIL_DOMAIN: tuple[str, str] = (By.NAME, "domain")
    PASSWORD: tuple[str, str] = (By.NAME, "password")
    PASSWORD_REPEAT: tuple[str, str] = (By.NAME, "passwordRetype")
    RECOVERY_EMAIL: tuple[str, str] = (By.NAME, "emailRecovery")
    BIRTH_DAY: tuple[str, str] = (By.NAME, "birthDay")
    BIRTH_MONTH: tuple[str, str] = (By.NAME, "birthMonth")
    BIRTH_YEAR: tuple[str, str] = (By.NAME, "birthYear")
    SECURITY_QUESTION: tuple[str, str] = (By.NAME, "securityQuestion")
    SECURITY_ANSWER: tuple[str, str] = (By.NAME, "securityAnswer")
    TERMS_CHECKBOX: tuple[str, str] = (By.NAME, "terms")
    PRIVACY_CHECKBOX: tuple[str, str] = (By.NAME, "privacy")
    SUBMIT_BUTTON: tuple[str, str] = (By.CSS_SELECTOR, "button[type='submit']")
    CAPTCHA_IFRAME: tuple[str, str] = (By.CSS_SELECTOR, "iframe[title*='captcha']")


SECURITY_QUESTION_LABELS: dict[str, str] = {
    "mother_maiden_name": "What is your mother's maiden name?",
    "first_pet": "What was the name of your first pet?",
    "birth_city": "In what city were you born?",
}


class GMXRegistrationPage(BasePage):
    def __init__(self, driver, base_url: str, default_timeout: int = 20) -> None:
        super().__init__(driver=driver, default_timeout=default_timeout)
        self.base_url = base_url
        self.locators = GMXRegistrationLocators()

    def open(self) -> None:
        root_url = "https://signup.gmx.com/"
        logger.info("Opening GMX root page first: %s", root_url)
        # Always visit the canonical root first so the site sees a consistent entry
        # point (analytics, cookies, geo routing, etc.). If the registration form
        # is present after visiting root we continue; otherwise fall back to the
        # configured base_url.
        try:
            self.driver.get(root_url)
            # quick probe: wait briefly for the first name field to appear
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(self.locators.FIRST_NAME)
            )
            logger.debug("Registration form available on root URL")
        except TimeoutException:
            logger.debug(
                "Form not present on root; navigating to configured base_url: %s",
                self.base_url,
            )
            self.driver.get(self.base_url)

        # Dismiss cookie banner on whichever page we're currently on
        self._dismiss_cookie_banner()

    def _dismiss_cookie_banner(self, timeout_s: int = 15) -> None:
        button_xpaths = (
            "//button[normalize-space()='Accept all']",
            "//button[normalize-space()='Alle akzeptieren']",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        )
        iframe_locators = (
            (By.CSS_SELECTOR, "iframe[src*='consent']"),
            (By.CSS_SELECTOR, "iframe[id^='sp_message_iframe']"),
            (By.CSS_SELECTOR, "iframe[data-testid='uc-consent-iframe']"),
        )

        def click_accept_button() -> bool:
            for button in self.driver.find_elements(
                By.ID, "onetrust-accept-btn-handler"
            ):
                try:
                    button.click()
                    logger.info("Accepted cookie consent via OneTrust button")
                    return True
                except WebDriverException as exc:
                    logger.debug("Failed to click OneTrust button: %s", exc)

            for xpath in button_xpaths:
                for button in self.driver.find_elements(By.XPATH, xpath):
                    try:
                        button.click()
                        logger.info("Accepted cookie consent banner")
                        return True
                    except WebDriverException as exc:
                        logger.debug(
                            "Failed to click consent button located via %s: %s",
                            xpath,
                            exc,
                        )
                        continue
            return False

        end_time = time.time() + timeout_s
        while time.time() < end_time:
            if click_accept_button():
                return

            for locator in iframe_locators:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.frame_to_be_available_and_switch_to_it(locator)
                    )
                    if click_accept_button():
                        self.driver.switch_to.default_content()
                        return
                except TimeoutException:
                    continue
                finally:
                    self.driver.switch_to.default_content()

            time.sleep(0.5)

    def fill_form(self, data: RegistrationData) -> None:
        logger.info("Filling signup form for %s", data.email_address)
        self.fill_field(self.locators.FIRST_NAME, data.first_name)
        self.fill_field(self.locators.LAST_NAME, data.last_name)
        self.fill_field(self.locators.EMAIL_LOCAL_PART, data.email_local_part)

        domain_dropdown = Select(self.wait_until_visible(self.locators.EMAIL_DOMAIN))
        try:
            domain_dropdown.select_by_value(data.email_domain)
        except NoSuchElementException:
            domain_dropdown.select_by_visible_text(data.email_domain)

        self.fill_field(self.locators.PASSWORD, data.password)
        self.fill_field(self.locators.PASSWORD_REPEAT, data.password)
        self.fill_field(self.locators.RECOVERY_EMAIL, data.recovery_email)

        Select(self.wait_until_visible(self.locators.BIRTH_MONTH)).select_by_value(
            f"{data.birthdate.month:02d}"
        )
        Select(self.wait_until_visible(self.locators.BIRTH_DAY)).select_by_value(
            f"{data.birthdate.day:02d}"
        )
        Select(self.wait_until_visible(self.locators.BIRTH_YEAR)).select_by_value(
            str(data.birthdate.year)
        )

        security_question_value = SECURITY_QUESTION_LABELS.get(data.security_question)
        if security_question_value:
            try:
                Select(
                    self.wait_until_visible(self.locators.SECURITY_QUESTION)
                ).select_by_visible_text(security_question_value)
            except NoSuchElementException:
                logger.warning(
                    "Security question option not found: %s", security_question_value
                )
        else:
            logger.warning(
                "Unsupported security question key: %s", data.security_question
            )

        self.fill_field(self.locators.SECURITY_ANSWER, data.security_answer)

        try:
            self.click(self.locators.TERMS_CHECKBOX)
        except TimeoutException:
            logger.warning("Terms checkbox not found; please verify the locator")

        try:
            self.click(self.locators.PRIVACY_CHECKBOX)
        except TimeoutException:
            logger.warning("Privacy checkbox not found; please verify the locator")

    def submit(self) -> None:
        logger.info("Submitting signup form")
        self.click(self.locators.SUBMIT_BUTTON)

    def wait_for_captcha(self) -> bool:
        """Return True if a captcha iframe appears and user attention is needed."""

        try:
            iframe = self.wait_until_visible(self.locators.CAPTCHA_IFRAME, timeout=5)
            logger.info(
                "Captcha iframe detected (id=%s). Manual intervention required.",
                iframe.get_attribute("id"),
            )
            return True
        except TimeoutException:
            logger.info("Captcha iframe not detected within timeout")
            return False
