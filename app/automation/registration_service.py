"""High-level orchestration for GMX account registration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from ..config import SeleniumConfig, load_config
from ..data_models import RegistrationData, RegistrationResult
from ..driver_factory import managed_driver
from .gmx_registration_page import GMXRegistrationPage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RegistrationOptions:
    """Runtime switches for the registration flow."""

    skip_submit: bool = False
    wait_for_manual_confirmation: bool = True
    success_url_fragment: str = "mail.gmx.com"


class RegistrationService:
    def __init__(self, config: SeleniumConfig | None = None) -> None:
        self.config = config or load_config()

    def register(
        self, data: RegistrationData, options: RegistrationOptions | None = None
    ) -> RegistrationResult:
        run_options = options or RegistrationOptions()

        with managed_driver(self.config) as driver:
            page = GMXRegistrationPage(
                driver, self.config.base_url, semi_auto=self.config.semi_auto
            )
            page.open()

            try:
                page.fill_form(data)
            except WebDriverException as exc:
                logger.exception("Failed to fill form due to WebDriver error")
                return RegistrationResult(
                    email_address=data.email_address,
                    success=False,
                    details=str(exc),
                )

            captcha_detected = page.wait_for_captcha()
            if captcha_detected:
                logger.info("Pause for manual captcha resolution before submission")

            if run_options.skip_submit:
                logger.info(
                    "skip_submit flag is set, returning without submitting the form"
                )
                return RegistrationResult(
                    email_address=data.email_address,
                    success=False,
                    details="Form filled. Submission skipped by configuration.",
                )

            if captcha_detected and run_options.wait_for_manual_confirmation:
                try:
                    input(
                        "Captcha detected. Solve it in the browser window and press Enter here to continue..."
                    )
                except EOFError:
                    logger.warning(
                        "STDIN unavailable. Continuing without manual pause."
                    )

            try:
                page.submit()
            except WebDriverException as exc:
                logger.exception("Submit failed due to WebDriver error")
                return RegistrationResult(
                    email_address=data.email_address,
                    success=False,
                    details=str(exc),
                )

            if not run_options.wait_for_manual_confirmation:
                return RegistrationResult(
                    email_address=data.email_address, success=True
                )

            try:
                WebDriverWait(driver, self.config.page_load_timeout_s).until(
                    lambda drv: run_options.success_url_fragment in drv.current_url
                )
                logger.info("Detected navigation to success page")
                return RegistrationResult(
                    email_address=data.email_address, success=True
                )
            except TimeoutException:
                logger.warning("Did not detect success URL within timeout")
                return RegistrationResult(
                    email_address=data.email_address,
                    success=False,
                    details="Success URL was not reached before timeout.",
                )
