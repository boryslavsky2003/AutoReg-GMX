"""GMX specific page object for the signup form."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..data_models import RegistrationData
from .base_page import BasePage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GMXRegistrationLocators:
    # Primary selectors (fallbacks handled in _find_form_element method)
    FIRST_NAME: tuple[str, str] = (
        By.CSS_SELECTOR,
        "input[data-test='first-name-input']",
    )
    LAST_NAME: tuple[str, str] = (By.CSS_SELECTOR, "input[data-test='last-name-input']")
    EMAIL_LOCAL_PART: tuple[str, str] = (By.NAME, "email")
    EMAIL_DOMAIN: tuple[str, str] = (By.NAME, "domain")
    PASSWORD: tuple[str, str] = (By.NAME, "password")
    PASSWORD_REPEAT: tuple[str, str] = (By.NAME, "passwordRetype")
    RECOVERY_EMAIL: tuple[str, str] = (By.NAME, "emailRecovery")

    # Birthday field selectors (confirmed working with provided HTML)
    BIRTH_MONTH: tuple[str, str] = (By.CSS_SELECTOR, "input[data-test='month']")
    BIRTH_DAY: tuple[str, str] = (By.CSS_SELECTOR, "input[data-test='day']")
    BIRTH_YEAR: tuple[str, str] = (By.CSS_SELECTOR, "input[data-test='year']")

    SECURITY_QUESTION: tuple[str, str] = (By.NAME, "securityQuestion")
    SECURITY_ANSWER: tuple[str, str] = (By.NAME, "securityAnswer")
    # Navigation buttons
    NEXT_BUTTON: tuple[str, str] = (
        By.XPATH,
        "//span[contains(@class, 'onereg-progress-meter__buttons-text') and text()='Next']",
    )

    # Second page email field
    EMAIL_INPUT: tuple[str, str] = (
        By.CSS_SELECTOR,
        "input[data-test='check-email-availability-email-input']",
    )

    # Error message selector
    ERROR_MESSAGE: tuple[str, str] = (
        By.XPATH,
        "//span[contains(text(), 'Something went wrong')]",
    )

    # Check email availability button
    CHECK_EMAIL_BUTTON: tuple[str, str] = (
        By.CSS_SELECTOR,
        "button[data-test='check-email-availability-check-button']",
    )

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
        print("\n" + "=" * 80)
        print(f"🎯 STARTING GMX REGISTRATION FOR: {data.first_name} {data.last_name}")
        print(f"📅 Date of Birth: {data.birthdate.strftime('%m/%d/%Y')}")
        print("=" * 80)

        logger.info(
            "Starting GMX registration for: %s %s", data.first_name, data.last_name
        )

        # FIRST PAGE: Only Name and Birthdate fields (no email on first page)

        print("\n📝 STEP 1/3: FILLING NAME FIELDS")
        print("-" * 40)

        # Try fast JavaScript filling first (faster method)
        js_success = self._fast_fill_name_fields(data.first_name, data.last_name)

        if not js_success:
            # Fallback to regular filling if JS fails
            # Fill First Name
            try:
                first_name_element = self._find_form_element("first_name")
                first_name_element.clear()
                first_name_element.send_keys(data.first_name)
                logger.info(f"✅ First name filled: {data.first_name}")
            except Exception as e:
                logger.error(f"❌ Failed to fill first name: {e}")
                # Fallback to original method
                self.fill_field(self.locators.FIRST_NAME, data.first_name)

            # Fill Last Name
            try:
                last_name_element = self._find_form_element("last_name")
                last_name_element.clear()
                last_name_element.send_keys(data.last_name)
                logger.info(f"✅ Last name filled: {data.last_name}")
            except Exception as e:
                logger.error(f"❌ Failed to fill last name: {e}")
                self.fill_field(self.locators.LAST_NAME, data.last_name)

        # Fill Date of Birth (MM, DD, YYYY format)
        month_str = f"{data.birthdate.month:02d}"
        day_str = f"{data.birthdate.day:02d}"
        year_str = str(data.birthdate.year)

        print("\n🗓️  STEP 2/3: FILLING BIRTHDATE")
        print("-" * 40)
        print(f"📅 Target Date: {month_str}/{day_str}/{year_str}")

        logger.info(f"Filling birthdate: {month_str}/{day_str}/{year_str}")

        # Try fast JavaScript method first
        js_birthdate_success = self._fast_fill_birthdate(month_str, day_str, year_str)

        if not js_birthdate_success:
            # Fallback to regular method
            try:
                # Find birthdate fields using confirmed working selectors
                month_element = self._find_birthdate_element("month")
                day_element = self._find_birthdate_element("day")
                year_element = self._find_birthdate_element("year")

                # Fill month (MM) - faster approach
                month_element.clear()
                time.sleep(0.05)  # Reduced delay
                month_element.send_keys(month_str)
                logger.info(f"✅ Month filled: {month_str}")

                # Fill day (DD) - faster approach
                day_element.clear()
                time.sleep(0.05)  # Reduced delay
                day_element.send_keys(day_str)
                logger.info(f"✅ Day filled: {day_str}")

                # Fill year (YYYY) - faster approach
                year_element.clear()
                time.sleep(0.05)  # Reduced delay
                year_element.send_keys(year_str)
                logger.info(f"✅ Year filled: {year_str}")

                # Verify all fields were filled correctly
                time.sleep(0.1)  # Reduced verification delay
                actual_month = month_element.get_attribute("value")
                actual_day = day_element.get_attribute("value")
                actual_year = year_element.get_attribute("value")

                if (
                    actual_month == month_str
                    and actual_day == day_str
                    and actual_year == year_str
                ):
                    logger.info(
                        f"✅ Birthdate verification SUCCESS: {actual_month}/{actual_day}/{actual_year}"
                    )
                else:
                    logger.warning(
                        f"⚠️  Birthdate verification MISMATCH: Expected {month_str}/{day_str}/{year_str}, Got {actual_month}/{actual_day}/{actual_year}"
                    )

            except Exception as e:
                logger.error(f"❌ Error filling birthdate fields: {e}")
                # Fallback: try alternative approach
                logger.info("🔄 Attempting alternative birthdate filling method...")
                self._fill_birthdate_alternative(data.birthdate)

        print("\n🚀 STEP 3/3: NAVIGATING TO NEXT PAGE")
        print("-" * 40)
        print("✅ First page completed successfully!")
        print("⏭️  Moving to email registration...")

        logger.info("First page filling complete - Name and Birthdate only")
        logger.info("Email and other fields will be on next page")

        # Click Next button to proceed to next page
        self._click_next_button()

        # Fill second page (email field)
        self._fill_second_page(data)

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

    def _fill_birthdate_alternative(self, birthdate) -> None:
        """Alternative method for filling birthdate fields."""
        try:
            logger.info("Trying alternative birthdate filling approach...")

            # Try using JavaScript to set values directly
            month_str = f"{birthdate.month:02d}"
            day_str = f"{birthdate.day:02d}"
            year_str = str(birthdate.year)

            # Use JavaScript to fill values with multiple selector attempts
            js_script = """
            // Try multiple selectors for each field
            const monthSelectors = ['input[data-test="month"]', 'input[id="bday-month"]', 'input[name="month"]', 'input[autocomplete="bday-month"]'];
            const daySelectors = ['input[data-test="day"]', 'input[id="bday-day"]', 'input[name="day"]', 'input[autocomplete="bday-day"]'];
            const yearSelectors = ['input[data-test="year"]', 'input[id="bday-year"]', 'input[name="year"]', 'input[autocomplete="bday-year"]'];
            
            let monthField = null;
            let dayField = null; 
            let yearField = null;
            
            // Find month field
            for (const selector of monthSelectors) {
                monthField = document.querySelector(selector);
                if (monthField) break;
            }
            
            // Find day field
            for (const selector of daySelectors) {
                dayField = document.querySelector(selector);
                if (dayField) break;
            }
            
            // Find year field
            for (const selector of yearSelectors) {
                yearField = document.querySelector(selector);
                if (yearField) break;
            }
            
            if (monthField) {
                monthField.value = arguments[0];
                monthField.dispatchEvent(new Event('input', { bubbles: true }));
                monthField.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (dayField) {
                dayField.value = arguments[1];
                dayField.dispatchEvent(new Event('input', { bubbles: true }));
                dayField.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (yearField) {
                yearField.value = arguments[2];
                yearField.dispatchEvent(new Event('input', { bubbles: true }));
                yearField.dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            return {
                monthFound: !!monthField,
                dayFound: !!dayField,
                yearFound: !!yearField
            };
            """

            result = self.driver.execute_script(js_script, month_str, day_str, year_str)
            logger.info(
                f"Alternative method: Set birthdate to {month_str}/{day_str}/{year_str}"
            )
            logger.info(f"JS execution result: {result}")

            # Give time for the form to process
            time.sleep(1)

        except Exception as e:
            logger.error(f"Alternative birthdate filling also failed: {e}")
            # Last resort: try clicking and typing
            try:
                self._fill_birthdate_manual_typing(birthdate)
            except Exception as e2:
                logger.error(f"Manual typing approach also failed: {e2}")
                raise WebDriverException(
                    f"All birthdate filling methods failed. Original error: {e}"
                )

    def _fill_birthdate_manual_typing(self, birthdate) -> None:
        """Manual typing approach for birthdate fields."""
        from selenium.webdriver.common.keys import Keys

        logger.info("Trying manual typing approach for birthdate...")

        month_str = f"{birthdate.month:02d}"
        day_str = f"{birthdate.day:02d}"
        year_str = str(birthdate.year)

        # Month field
        try:
            month_element = self._find_birthdate_element("month")
            month_element.click()
            time.sleep(0.3)
            month_element.send_keys(Keys.CONTROL + "a")  # Select all
            time.sleep(0.1)
            month_element.send_keys(month_str)
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"Failed to fill month: {e}")

        # Day field
        try:
            day_element = self._find_birthdate_element("day")
            day_element.click()
            time.sleep(0.3)
            day_element.send_keys(Keys.CONTROL + "a")
            time.sleep(0.1)
            day_element.send_keys(day_str)
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"Failed to fill day: {e}")

        # Year field
        try:
            year_element = self._find_birthdate_element("year")
            year_element.click()
            time.sleep(0.3)
            year_element.send_keys(Keys.CONTROL + "a")
            time.sleep(0.1)
            year_element.send_keys(year_str)
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"Failed to fill year: {e}")

        logger.info(f"Manual typing completed for {month_str}/{day_str}/{year_str}")

    def _find_birthdate_element(self, field_type: str):
        """Find birthdate element with multiple selector fallbacks."""
        selectors = {
            "month": [
                "input[data-test='month']",
                "input[id='bday-month']",
                "input[name='month']",
                "input[autocomplete='bday-month']",
                ".pos-dob--mm",
            ],
            "day": [
                "input[data-test='day']",
                "input[id='bday-day']",
                "input[name='day']",
                "input[autocomplete='bday-day']",
                ".pos-dob--dd",
            ],
            "year": [
                "input[data-test='year']",
                "input[id='bday-year']",
                "input[name='year']",
                "input[autocomplete='bday-year']",
                ".pos-dob--yyyy",
            ],
        }

        if field_type not in selectors:
            raise ValueError(f"Invalid field type: {field_type}")

        for selector in selectors[field_type]:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    logger.debug(f"Found {field_type} field with selector: {selector}")
                    return element
            except Exception:
                continue

        raise NoSuchElementException(
            f"Could not find {field_type} birthdate field with any selector"
        )

    def _find_form_element(self, element_type: str):
        """Find form element with multiple selector fallbacks."""
        selectors = {
            "first_name": [
                "input[data-test='first-name-input']",
                "input[name='firstName']",
                "input[id='firstName']",
                "input[placeholder*='first' i]",
                "#first-name-input",
            ],
            "last_name": [
                "input[data-test='last-name-input']",
                "input[name='lastName']",
                "input[id='lastName']",
                "input[placeholder*='last' i]",
                "#last-name-input",
            ],
            "email": [
                "input[name='email']",
                "input[data-test='email-input']",
                "input[type='email']",
                "input[id*='email']",
                "input[placeholder*='email' i]",
            ],
            "password": [
                "input[name='password']",
                "input[type='password']",
                "input[data-test='password-input']",
                "input[id*='password']",
            ],
            "password_repeat": [
                "input[name='passwordRetype']",
                "input[name='passwordRepeat']",
                "input[name='confirmPassword']",
                "input[data-test='password-repeat']",
                "input[id*='confirm']",
            ],
            "recovery_email": [
                "input[name='emailRecovery']",
                "input[name='recoveryEmail']",
                "input[data-test='recovery-email']",
                "input[placeholder*='recovery' i]",
            ],
        }

        if element_type not in selectors:
            raise ValueError(f"Invalid element type: {element_type}")

        for selector in selectors[element_type]:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    logger.debug(
                        f"Found {element_type} field with selector: {selector}"
                    )
                    return element
            except Exception:
                continue

        raise NoSuchElementException(
            f"Could not find {element_type} form field with any selector"
        )

    def _click_next_button(self) -> None:
        """Click the Next button to proceed to the next page."""
        try:
            logger.info("🔄 Clicking Next button to proceed to next page...")

            # Try multiple selectors for Next button
            next_selectors = [
                "//span[contains(@class, 'onereg-progress-meter__buttons-text') and text()='Next']",
                "//button[contains(., 'Next')]",
                "//span[text()='Next']",
                "//button[contains(@class, 'next')]",
                "[data-test*='next']",
                ".next-button",
            ]

            next_clicked = False
            for selector in next_selectors:
                try:
                    if selector.startswith("//"):
                        # XPath selector
                        element = self.driver.find_element(By.XPATH, selector)
                    else:
                        # CSS selector
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)

                    if element.is_displayed() and element.is_enabled():
                        # Try clicking the element
                        element.click()
                        logger.info(
                            f"✅ Successfully clicked Next button using selector: {selector}"
                        )
                        next_clicked = True
                        break

                except Exception as e:
                    logger.debug(f"Failed to click Next with selector {selector}: {e}")
                    continue

            if not next_clicked:
                logger.warning("⚠️  Could not find or click Next button")
                # Try to find any clickable button that might be Next
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = button.text.strip().lower()
                            if (
                                "next" in button_text
                                or "weiter" in button_text
                                or "continuer" in button_text
                            ):
                                button.click()
                                logger.info(
                                    f"✅ Found and clicked Next button by text: {button.text}"
                                )
                                next_clicked = True
                                break
                except Exception as e:
                    logger.error(f"Failed to find Next button by text search: {e}")

            if next_clicked:
                # Wait a moment for page transition (reduced from 2 to 1 sec)
                time.sleep(1)
                logger.info("📄 Proceeding to next page...")
            else:
                logger.error("❌ Failed to click Next button with all methods")

        except Exception as e:
            logger.error(f"❌ Unexpected error clicking Next button: {e}")
            raise

    def _fast_fill_name_fields(self, first_name: str, last_name: str) -> bool:
        """Fast filling of name fields using JavaScript. Returns True if successful."""
        try:
            logger.info("🚀 Using fast JavaScript filling for name fields...")

            js_script = """
            // Find first name field
            const firstNameSelectors = [
                'input[data-test="first-name-input"]',
                'input[name="firstName"]',
                'input[id*="first"]',
                'input[placeholder*="first" i]'
            ];
            
            // Find last name field  
            const lastNameSelectors = [
                'input[data-test="last-name-input"]',
                'input[name="lastName"]',
                'input[id*="last"]',
                'input[placeholder*="last" i]'
            ];
            
            let firstNameField = null;
            let lastNameField = null;
            
            // Find first name field
            for (const selector of firstNameSelectors) {
                firstNameField = document.querySelector(selector);
                if (firstNameField && firstNameField.offsetParent !== null) break;
            }
            
            // Find last name field
            for (const selector of lastNameSelectors) {
                lastNameField = document.querySelector(selector);
                if (lastNameField && lastNameField.offsetParent !== null) break;
            }
            
            if (firstNameField && lastNameField) {
                // Fill first name
                firstNameField.value = arguments[0];
                firstNameField.dispatchEvent(new Event('input', { bubbles: true }));
                firstNameField.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Fill last name  
                lastNameField.value = arguments[1];
                lastNameField.dispatchEvent(new Event('input', { bubbles: true }));
                lastNameField.dispatchEvent(new Event('change', { bubbles: true }));
                
                return true;
            }
            return false;
            """

            result = self.driver.execute_script(js_script, first_name, last_name)

            if result:
                logger.info(f"✅ Fast JS fill SUCCESS: {first_name} {last_name}")
                return True
            else:
                logger.info(
                    "⚠️  JS fill failed - fields not found, using fallback method"
                )
                return False

        except Exception as e:
            logger.warning(f"⚠️  JavaScript filling failed: {e}, using fallback method")
            return False

    def _fast_fill_birthdate(self, month: str, day: str, year: str) -> bool:
        """Fast filling of birthdate fields using JavaScript. Returns True if successful."""
        try:
            logger.info("🚀 Using fast JavaScript filling for birthdate fields...")

            js_script = """
            // Multiple selectors for each birthdate field
            const monthSelectors = [
                'input[data-test="month"]',
                'input[id="bday-month"]', 
                'input[name="month"]',
                'input[autocomplete="bday-month"]',
                '.pos-dob--mm'
            ];
            
            const daySelectors = [
                'input[data-test="day"]',
                'input[id="bday-day"]',
                'input[name="day"]', 
                'input[autocomplete="bday-day"]',
                '.pos-dob--dd'
            ];
            
            const yearSelectors = [
                'input[data-test="year"]',
                'input[id="bday-year"]',
                'input[name="year"]',
                'input[autocomplete="bday-year"]', 
                '.pos-dob--yyyy'
            ];
            
            let monthField = null;
            let dayField = null;
            let yearField = null;
            
            // Find month field
            for (const selector of monthSelectors) {
                monthField = document.querySelector(selector);
                if (monthField && monthField.offsetParent !== null) break;
            }
            
            // Find day field
            for (const selector of daySelectors) {
                dayField = document.querySelector(selector);
                if (dayField && dayField.offsetParent !== null) break;
            }
            
            // Find year field
            for (const selector of yearSelectors) {
                yearField = document.querySelector(selector);
                if (yearField && yearField.offsetParent !== null) break;
            }
            
            if (monthField && dayField && yearField) {
                // Fill month
                monthField.value = arguments[0];
                monthField.dispatchEvent(new Event('input', { bubbles: true }));
                monthField.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Fill day
                dayField.value = arguments[1];
                dayField.dispatchEvent(new Event('input', { bubbles: true }));
                dayField.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Fill year
                yearField.value = arguments[2];
                yearField.dispatchEvent(new Event('input', { bubbles: true }));
                yearField.dispatchEvent(new Event('change', { bubbles: true }));
                
                return true;
            }
            return false;
            """

            result = self.driver.execute_script(js_script, month, day, year)

            if result:
                logger.info(f"✅ Fast JS birthdate fill SUCCESS: {month}/{day}/{year}")
                return True
            else:
                logger.info(
                    "⚠️  JS birthdate fill failed - fields not found, using fallback method"
                )
                return False

        except Exception as e:
            logger.warning(
                f"⚠️  JavaScript birthdate filling failed: {e}, using fallback method"
            )
            return False

    def _fill_second_page(self, data: RegistrationData) -> None:
        """Fill the second page fields (email)."""
        print("\n" + "=" * 80)
        print("📧 SECOND PAGE: EMAIL REGISTRATION")
        print("=" * 80)

        # Simulate reading the page before starting
        print("📖 Reading page content...")
        time.sleep(random.uniform(3.0, 7.0))

        logger.info(
            "Starting second page - Email field"
        )  # Wait for second page to load
        time.sleep(1.5)

        # Generate and fill email with retry logic (increased attempts)
        max_attempts = 10  # Increased from 5 to 10 for better success rate
        for attempt in range(1, max_attempts + 1):
            progress = "█" * attempt + "░" * (max_attempts - attempt)
            print(f"\n📧 EMAIL ATTEMPT {attempt}/{max_attempts} [{progress}]")
            print("-" * 60)

            logger.info(f"Email filling attempt {attempt}/{max_attempts}")

            # Generate email address
            email_local = self._generate_email_local_part(data, attempt)

            # Fill email field
            success = self._fill_email_field(email_local)

            if success:
                # Add human-like delay and behavior to avoid bot detection
                self._simulate_human_behavior_before_check()
                if self._check_for_email_error():
                    logger.warning(
                        f"⚠️  Email {email_local} failed - 'Something went wrong' error detected"
                    )
                    if attempt < max_attempts:
                        logger.info("🔄 Trying with different email variant...")
                        continue
                    else:
                        logger.error("❌ All email attempts failed")
                        break
                else:
                    logger.info(f"✅ Email {email_local} filled successfully")
                    # Simulate human-like behavior before checking
                    self._simulate_typing_pause()
                    # Click Check button to verify availability
                    if self._click_check_button():
                        # Wait and check if email is available
                        time.sleep(2)
                        if self._check_email_availability():
                            print(f"🎉 SUCCESS! {email_local}@gmx.com is AVAILABLE!")
                            print("=" * 60)
                            logger.info(f"Email {email_local} is AVAILABLE")
                            break
                        else:
                            print(f"❌ {email_local}@gmx.com is TAKEN")
                            print("⏭️  Trying next variant...")

                            # Add increasing delays between failed attempts to avoid being flagged
                            failure_delay = random.uniform(
                                15.0 + (attempt * 5), 30.0 + (attempt * 10)
                            )
                            print(
                                f"⏳ Cooling down for {failure_delay:.1f}s to avoid detection..."
                            )
                            time.sleep(failure_delay)

                            logger.warning(
                                f"Email {email_local} is TAKEN - trying next variant after cooldown"
                            )
                            if attempt < max_attempts:
                                continue
                            else:
                                print("\n💥 ALL EMAIL ATTEMPTS EXHAUSTED!")
                                print(f"❌ Tried {max_attempts} different variations")
                                print(
                                    "🔄 Consider using different name/date combination"
                                )
                                print("=" * 60)
                                logger.error("All email attempts failed - all taken")
                                break
                    else:
                        logger.error("❌ Failed to click Check button")
                        break
            else:
                logger.error(f"❌ Failed to fill email field on attempt {attempt}")
                if attempt < max_attempts:
                    time.sleep(1)
                    continue
                else:
                    break

    pass

    def _add_human_randomness_to_email(self, base_email: str, attempt: int) -> str:
        """Add human-like randomness to email generation to avoid predictable patterns."""
        import random
        import string

        # For later attempts, add more randomness to avoid bot detection
        if attempt > 2:
            # Add random digits for attempts 3+
            random_digits = "".join(
                random.choices(string.digits, k=random.randint(1, 3))
            )
            base_email += random_digits
            logger.info(f"🎲 Added random digits: {random_digits}")

        if attempt > 5:
            # Add random letters for attempts 6+
            random_letters = "".join(random.choices(string.ascii_lowercase, k=2))
            base_email += random_letters
            logger.info(f"🎲 Added random letters: {random_letters}")

        # Sometimes add underscores or dots for variety (10% chance)
        if attempt > 3 and random.random() < 0.1:
            if not base_email.endswith("_") and not base_email.endswith("."):
                separator = random.choice(["_", "."])
                extra_chars = "".join(random.choices(string.digits, k=2))
                base_email += separator + extra_chars
                logger.info(f"🎲 Added separator: {separator}{extra_chars}")

        return base_email

    def _generate_email_local_part(self, data: RegistrationData, attempt: int) -> str:
        """Generate email local part based on name and birthdate with variations."""
        import random
        import string

        first_name = data.first_name.lower().replace(" ", "")
        last_name = data.last_name.lower().replace(" ", "")
        birth_year = str(data.birthdate.year)
        birth_month = f"{data.birthdate.month:02d}"
        birth_day = f"{data.birthdate.day:02d}"

        # Different patterns for each attempt
        patterns = [
            f"{first_name}{last_name}{birth_year}",  # john.smith1995
            f"{first_name}.{last_name}{birth_year}",  # john.smith1995
            f"{first_name}{birth_year}{birth_month}",  # john199512
            f"{last_name}{first_name}{birth_day}",  # smithjohn25
            f"{first_name[0]}{last_name}{birth_year}",  # jsmith1995
            f"{first_name}{last_name[0]}{birth_year}",  # johns1995
            f"{first_name}_{last_name}{birth_year}",  # john_smith1995
            f"{first_name}{last_name}{birth_month}{birth_day}",  # johnsmith1225
        ]

        # Select pattern based on attempt
        pattern_index = (attempt - 1) % len(patterns)
        base_email = patterns[pattern_index]

        # Add random suffix for additional uniqueness
        if attempt > len(patterns):
            random_suffix = "".join(random.choices(string.digits, k=2))
            base_email += random_suffix

        # Add human-like randomness to make it less predictable
        base_email = self._add_human_randomness_to_email(base_email, attempt)

        # Ensure it's not too long (most email providers limit to 64 chars)
        if len(base_email) > 30:
            base_email = base_email[:30]

        print(f"🎯 Generated: {base_email}@gmx.com (Pattern #{pattern_index + 1})")
        logger.info(
            f"Generated email local part: {base_email} (pattern {pattern_index + 1})"
        )
        return base_email

    def _simulate_typing_mistake_and_correction(self, email_local: str) -> None:
        """Simulate human typing mistakes and corrections to appear more natural."""
        print("🤔 Simulating typing mistake...")

        # Simulate typing wrong email first
        wrong_email = email_local + "x"  # Add extra character
        self._fast_fill_email_field(wrong_email)

        # Pause as if realizing the mistake
        time.sleep(random.uniform(1.0, 3.0))
        print("✏️ Correcting typing mistake...")

        # Clear and type correct email
        time.sleep(random.uniform(0.5, 1.5))

    def _fill_email_field(self, email_local: str) -> bool:
        """Fill the email input field. Returns True if successful."""
        try:
            # Try fast JavaScript fill first
            js_success = self._fast_fill_email_field(email_local)
            if js_success:
                return True

            # Fallback to regular Selenium
            email_field = self.driver.find_element(*self.locators.EMAIL_INPUT)
            email_field.clear()
            time.sleep(0.1)
            email_field.send_keys(email_local)
            logger.info(f"✅ Email field filled: {email_local}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to fill email field: {e}")
            return False

    def _fast_fill_email_field(self, email_local: str) -> bool:
        """Fast JavaScript filling of email field."""
        try:
            logger.info("🚀 Using fast JavaScript filling for email field...")

            js_script = """
            // Multiple selectors for email field
            const emailSelectors = [
                'input[data-test="check-email-availability-email-input"]',
                'input[formcontrolname="alias"]',
                'input[class*="email-alias-advanced-input__alias-text-input"]',
                'input[type="text"][autocomplete="off"]'
            ];
            
            let emailField = null;
            
            // Find email field
            for (const selector of emailSelectors) {
                emailField = document.querySelector(selector);
                if (emailField && emailField.offsetParent !== null) break;
            }
            
            if (emailField) {
                emailField.value = arguments[0];
                emailField.dispatchEvent(new Event('input', { bubbles: true }));
                emailField.dispatchEvent(new Event('change', { bubbles: true }));
                emailField.dispatchEvent(new Event('blur', { bubbles: true }));
                return true;
            }
            return false;
            """

            result = self.driver.execute_script(js_script, email_local)

            if result:
                logger.info(f"✅ Fast JS email fill SUCCESS: {email_local}")
                return True
            else:
                logger.info("⚠️  JS email fill failed - field not found, using fallback")
                return False

        except Exception as e:
            logger.warning(f"⚠️  JavaScript email filling failed: {e}")
            return False

    def _check_for_email_error(self) -> bool:
        """Check if 'Something went wrong' error appears. Returns True if error found."""
        try:
            # Check for error message
            error_elements = self.driver.find_elements(*self.locators.ERROR_MESSAGE)
            if error_elements:
                for element in error_elements:
                    if (
                        element.is_displayed()
                        and "something went wrong" in element.text.lower()
                    ):
                        logger.warning(f"🚨 Error detected: {element.text}")
                        return True

            # Also check for any error-related classes or attributes
            error_indicators = [
                "[class*='error']",
                "[class*='invalid']",
                ".error-message",
                ".ng-invalid",
            ]

            for selector in error_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if (
                            element.is_displayed()
                            and element.text
                            and "something went wrong" in element.text.lower()
                        ):
                            logger.warning(
                                f"🚨 Error found via selector {selector}: {element.text}"
                            )
                            return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.debug(f"Error checking failed: {e}")
            return False

    def _click_check_button(self) -> bool:
        """Click the Check button to verify email availability. Returns True if successful."""
        print("🔍 Checking email availability...")
        logger.info("Clicking Check button to verify email availability")

        try:
            # Wait for Check button to be clickable
            check_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.locators.CHECK_EMAIL_BUTTON)
            )

            # Check if button is enabled
            if check_button.get_attribute("disabled") is None:
                check_button.click()
                logger.info("✅ Successfully clicked Check button")
                return True
            else:
                logger.warning("⚠️  Check button is disabled")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to click Check button: {e}")
            # Try alternative methods
            return self._click_check_button_fallback()

    def _click_check_button_fallback(self) -> bool:
        """Fallback method to click Check button using JavaScript."""
        try:
            logger.info("🔄 Trying fallback method to click Check button...")

            js_script = """
            // Find Check button with multiple selectors
            const checkSelectors = [
                'button[data-test="check-email-availability-check-button"]',
                'button[class*="email-alias-advanced-input__check"]',
                'button[pos-button="cta"]',
                'button:contains("Check")'
            ];
            
            let checkButton = null;
            
            for (const selector of checkSelectors) {
                if (selector.includes(':contains')) {
                    // Handle jQuery-style selector
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        if (btn.textContent.includes('Check') && 
                            !btn.disabled && 
                            btn.offsetParent !== null) {
                            checkButton = btn;
                            break;
                        }
                    }
                } else {
                    checkButton = document.querySelector(selector);
                }
                
                if (checkButton && !checkButton.disabled && checkButton.offsetParent !== null) {
                    break;
                }
                checkButton = null;
            }
            
            if (checkButton) {
                checkButton.click();
                return true;
            }
            return false;
            """

            result = self.driver.execute_script(js_script)

            if result:
                logger.info("✅ Successfully clicked Check button via JavaScript")
                return True
            else:
                logger.error(
                    "❌ Failed to click Check button - button not found or disabled"
                )
                return False

        except Exception as e:
            logger.error(f"❌ JavaScript Check button click failed: {e}")
            return False

    def _check_email_availability(self) -> bool:
        """Check if email is available after clicking Check. Returns True if available."""
        print("📋 Analyzing response...")
        logger.info("Checking email availability result")

        try:
            # Wait for response
            time.sleep(2)

            # Check for various indicators of email being taken or bot detected
            taken_indicators = [
                "//span[contains(text(), 'taken')]",
                "//span[contains(text(), 'unavailable')]",
                "//span[contains(text(), 'already exists')]",
                "//div[contains(@class, 'error')]",
                "//div[contains(text(), 'not available')]",
                "//span[contains(text(), 'зайнято')]",  # Ukrainian
                "//span[contains(text(), 'занято')]",  # Russian
                # Bot detection messages
                "//span[contains(text(), 'sorry, that didn't work')]",
                "//span[contains(text(), 'Please try again later')]",
                "//div[contains(text(), 'try again later')]",
                "//span[contains(text(), 'temporarily unavailable')]",
            ]

            for indicator in taken_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    for element in elements:
                        if element.is_displayed():
                            print(f"🚫 Found: {element.text}")
                            logger.warning(
                                f"Email taken indicator found: {element.text}"
                            )
                            return False
                except Exception:
                    continue

            # Check if Check button is disabled (often indicates taken email)
            try:
                check_button = self.driver.find_element(
                    *self.locators.CHECK_EMAIL_BUTTON
                )
                if check_button.get_attribute("disabled") is not None:
                    logger.warning("🚫 Check button is disabled - email likely taken")
                    return False
            except Exception:
                pass

            # Check for success indicators
            success_indicators = [
                "//span[contains(text(), 'available')]",
                "//span[contains(text(), 'good')]",
                "//div[contains(@class, 'success')]",
                "//span[contains(text(), 'доступно')]",  # Ukrainian
                "//span[contains(text(), 'доступен')]",  # Russian
            ]

            for indicator in success_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    for element in elements:
                        if element.is_displayed():
                            print(f"✅ Found: {element.text}")
                            logger.info(
                                f"Email available indicator found: {element.text}"
                            )
                            return True
                except Exception:
                    continue

            # If no clear indicators, assume available (conservative approach)
            logger.info(
                "ℹ️  No clear availability indicators found - assuming available"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error checking email availability: {e}")
            # On error, assume available to continue process
            return True

    def _simulate_human_behavior_before_check(self) -> None:
        """Simulate human-like behavior to avoid bot detection."""
        import random

        logger.info("🤖 Simulating human behavior to avoid bot detection...")

        # Random delay between 2 and 5 seconds (longer to seem more human)
        delay = random.uniform(2.0, 5.0)
        logger.info(f"⏱️  Waiting {delay:.1f}s before action (human-like timing)")
        time.sleep(delay)

        # Simulate mouse movement over the field
        try:
            email_field = self.driver.find_element(*self.locators.EMAIL_INPUT)
            from selenium.webdriver.common.action_chains import ActionChains

            actions = ActionChains(self.driver)
            actions.move_to_element(email_field)
            actions.pause(random.uniform(0.3, 1.0))
            actions.perform()
            logger.info("🖱️  Simulated mouse movement")
        except Exception:
            pass

    def _simulate_typing_pause(self) -> None:
        """Simulate natural typing pause after filling email."""
        import random

        # Random pause like human would do after typing (longer)
        pause = random.uniform(1.5, 3.5)
        logger.info(f"⏸️  Natural typing pause: {pause:.1f}s")
        time.sleep(pause)

        # Sometimes simulate re-reading what was typed
        if random.random() < 0.4:  # 40% chance
            logger.info("👀 Simulating re-reading typed text...")
            try:
                email_field = self.driver.find_element(*self.locators.EMAIL_INPUT)
                # Focus on field briefly
                email_field.click()
                time.sleep(random.uniform(0.8, 1.8))
            except Exception:
                pass

    def _simulate_human_behavior_before_check(self) -> None:
        """Simulate human-like behavior to avoid bot detection."""
        import random

        logger.info("🤖 Simulating human behavior to avoid bot detection...")

        # Random delay between 1.5 and 4 seconds
        delay = random.uniform(1.5, 4.0)
        logger.info(f"⏱️  Waiting {delay:.1f}s before action (human-like timing)")
        time.sleep(delay)

        # Simulate mouse movement over the field (optional visual cue)
        try:
            email_field = self.driver.find_element(*self.locators.EMAIL_INPUT)
            # Move to the field and back to simulate checking
            from selenium.webdriver.common.action_chains import ActionChains

            actions = ActionChains(self.driver)
            actions.move_to_element(email_field)
            actions.pause(random.uniform(0.2, 0.8))
            actions.perform()
            logger.info("🖱️  Simulated mouse movement")
        except Exception:
            pass

    def _simulate_typing_pause(self) -> None:
        """Simulate natural typing pause after filling email."""
        import random

        # Random pause like human would do after typing
        pause = random.uniform(0.8, 2.5)
        logger.info(f"⏸️  Natural typing pause: {pause:.1f}s")
        time.sleep(pause)

        # Sometimes simulate re-reading what was typed
        if random.random() < 0.3:  # 30% chance
            logger.info("👀 Simulating re-reading typed text...")
            try:
                email_field = self.driver.find_element(*self.locators.EMAIL_INPUT)
                # Focus on field briefly
                email_field.click()
                time.sleep(random.uniform(0.5, 1.2))
            except Exception:
                pass

    def _add_human_randomness_to_email(self, base_email: str, attempt: int) -> str:
        """Add human-like randomness to email generation."""
        import random
        import string

        # For later attempts, add more randomness
        if attempt > 2:
            # Add random digits
            random_digits = "".join(
                random.choices(string.digits, k=random.randint(2, 4))
            )
            base_email += random_digits

        if attempt > 4:
            # Add random letters for high attempts
            random_letters = "".join(random.choices(string.ascii_lowercase, k=2))
            base_email += random_letters

        return base_email
