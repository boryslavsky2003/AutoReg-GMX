"""GMX specific page object for the signup form."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

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
        logger.info("Opening GMX signup page: %s", self.base_url)
        self.driver.get(self.base_url)

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
