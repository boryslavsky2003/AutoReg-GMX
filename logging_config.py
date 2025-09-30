"""
Красива конфігурація логування для GMX автореєстрації
"""

import logging
import sys
from typing import Dict, Any


class ColorFormatter(logging.Formatter):
    """Форматер з кольорами для консолі"""

    # ANSI коди кольорів
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record):
        # Додаємо кольор до повідомлення
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # Форматуємо час
        formatted_time = self.formatTime(record, "%H:%M:%S")

        # Скорочуємо назву логера для зручності
        logger_name = record.name
        if logger_name.startswith("app."):
            logger_name = logger_name.replace("app.automation.", "")
            logger_name = logger_name.replace("app.", "")

        # Створюємо форматоване повідомлення
        formatted_msg = f"{color}{formatted_time} | {record.levelname:^8} | {logger_name:20} | {record.getMessage()}{reset}"

        return formatted_msg


def setup_logging() -> None:
    """Налаштовує красиве логування з фільтруванням зайвих повідомлень"""

    # Створюємо кореневий логер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Очищаємо існуючі хендлери
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Створюємо консольний хендлер з кольоровим форматером
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColorFormatter())

    # Додаємо хендлер до кореневого логера
    root_logger.addHandler(console_handler)

    # Налаштовуємо рівні логування для різних модулів
    logging_levels = {
        # Приховуємо зайві selenium-wire логи
        "seleniumwire.handler": logging.WARNING,
        "seleniumwire.server": logging.WARNING,
        "seleniumwire.capture": logging.WARNING,
        # Приховуємо зайві urllib3 логи
        "urllib3.connectionpool": logging.WARNING,
        "urllib3.util.retry": logging.WARNING,
        # Приховуємо зайві selenium логи
        "selenium.webdriver.remote.remote_connection": logging.WARNING,
        "selenium.webdriver.common.selenium_manager": logging.WARNING,
        # Показуємо тільки важливі логи наших модулів
        "app": logging.INFO,
        "app.automation": logging.INFO,
        "app.automation.gmx_registration_page": logging.INFO,
        "app.automation.registration_service": logging.INFO,
        # Кореневий логер
        "": logging.INFO,
    }

    # Застосовуємо рівні логування
    for logger_name, level in logging_levels.items():
        logging.getLogger(logger_name).setLevel(level)

    print("🎨 Красиве логування налаштовано!")
    print("=" * 80)


def log_section_start(title: str, emoji: str = "🔥") -> None:
    """Виводить красивий заголовок секції"""
    print("\n" + "=" * 80)
    print(f"{emoji} {title}")
    print("=" * 80)


def log_section_end(title: str = "", success: bool = True) -> None:
    """Виводить кінець секції"""
    emoji = "✅" if success else "❌"
    status = "COMPLETED" if success else "FAILED"

    print("=" * 80)
    if title:
        print(f"{emoji} {title} - {status}")
    else:
        print(f"{emoji} SECTION {status}")
    print("=" * 80 + "\n")


def log_progress_bar(
    current: int,
    total: int,
    prefix: str = "Progress",
    suffix: str = "Complete",
    length: int = 50,
) -> str:
    """Створює ASCII прогрес-бар"""
    percent = f"{100 * (current / float(total)):.1f}"
    filled_length = int(length * current // total)
    bar = "█" * filled_length + "░" * (length - filled_length)

    return f"\r{prefix} |{bar}| {percent}% {suffix}"


# Експортуємо основні функції
__all__ = ["setup_logging", "log_section_start", "log_section_end", "log_progress_bar"]
