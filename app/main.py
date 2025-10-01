"""Command line entrypoint for the AutoReg-GMX automation."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from typing import Any

# Налаштовуємо красиве логування
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    from logging_config import setup_logging

    setup_logging()
except ImportError:
    pass  # Fallback до стандартного логування

from .automation.registration_service import RegistrationOptions, RegistrationService
from .config import SeleniumConfig, load_config
from .data_models import RegistrationData, generate_registration_data
from .driver_factory import ChromeBinaryNotFoundError
from .env_loader import EnvFileNotFoundError, ensure_env_loaded
from .logging_config import configure_logging
from .utils.proxy import (
    ProxyFormatError,
    ProxyValidationError,
    ensure_proxy_connectivity,
    normalise_proxy_url,
)
from .storage.credential_store import CredentialStore, CredentialStoreError


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GMX registration automation helper")
    parser.add_argument(
        "--locale", default="en_US", help="Faker locale for generated data"
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        help="Optional path to JSON file with registration payload",
    )
    parser.add_argument(
        "--skip-submit",
        action="store_true",
        help="Do not click the final submit button (useful for manual review)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Do not wait for success page after submitting",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Force headed browser mode even if the config defaults to headless",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Force headless browser mode regardless of config",
    )
    parser.add_argument(
        "--success-url-fragment",
        default="mail.gmx.com",
        help="URL fragment indicating successful signup",
    )
    parser.add_argument(
        "--dump-json",
        action="store_true",
        help="Print the used registration payload as JSON at the end",
    )
    parser.add_argument(
        "--proxy",
        help="Proxy URL (http/https/socks5) to route browser traffic through",
    )
    return parser.parse_args(argv)


def _load_registration_from_file(path: Path) -> RegistrationData:
    payload = json.loads(path.read_text(encoding="utf-8"))
    birthdate_raw = payload.get("birthdate")
    if isinstance(birthdate_raw, str):
        birthdate = date.fromisoformat(birthdate_raw)
    else:
        raise ValueError(
            "birthdate must be an ISO formatted string in the JSON payload"
        )

    return RegistrationData(
        first_name=payload["first_name"],
        last_name=payload["last_name"],
        email_local_part=payload["email_local_part"],
        email_domain=payload["email_domain"],
        password=payload["password"],
        recovery_email=payload["recovery_email"],
        birthdate=birthdate,
        security_question=payload["security_question"],
        security_answer=payload["security_answer"],
    )


def _resolve_config(args: argparse.Namespace) -> SeleniumConfig:
    config = load_config()
    if args.headless and args.headed:
        raise ValueError("--headed and --headless cannot be used together")

    proxy_arg = args.proxy.strip() if getattr(args, "proxy", None) else None

    if args.headless:
        config = replace(config, headless=True)
    elif args.headed:
        config = replace(config, headless=False)

    if proxy_arg is not None:
        scheme_override = os.getenv("GMX_PROXY_SCHEME")
        if scheme_override and scheme_override.strip():
            default_scheme = scheme_override.strip().lower()
        else:
            default_scheme = config.proxy_scheme

        try:
            proxy_url = normalise_proxy_url(proxy_arg, default_scheme=default_scheme)
        except ProxyFormatError as exc:
            raise ValueError(f"Invalid --proxy value: {exc}") from exc

        config = replace(
            config,
            proxy_url=proxy_url,
            use_proxy=True,
            proxy_scheme=proxy_url.split("://", 1)[0].lower(),
        )
    elif not config.use_proxy:
        config = replace(config, proxy_url=None)

    return config


def main(argv: list[str] | None = None) -> int:
    # Вітаємо користувача
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          🚀 AutoReg-GMX v2.0                                ║
║                      Автоматична реєстрація GMX акаунтів                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    args = _parse_args(argv)

    try:
        ensure_env_loaded()
        print("✅ Environment loaded successfully")
    except EnvFileNotFoundError as exc:
        print(f"❌ ERROR: {exc}", file=sys.stderr)
        return 1

    print("\n🔧 Configuring application...")
    try:
        config = _resolve_config(args)
        print("✅ Configuration loaded")
    except ValueError as exc:
        print(f"❌ Configuration ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        credential_store = CredentialStore(config.credentials_db_path)
        print("✅ Database connection established")
    except CredentialStoreError as exc:
        logging.error("%s", exc)
        print(f"❌ Database ERROR: {exc}", file=sys.stderr)
        return 1

    if config.use_proxy and not config.proxy_url:
        print(
            "❌ PROXY ERROR: GMX_PROXY_URL is missing from .env. Please add your proxy URL.",
            file=sys.stderr,
        )
        return 1

    configure_logging()

    print(f"🔧 Browser: {'Headless' if config.headless else 'GUI'} mode")
    if config.proxy_url:
        print(f"🌐 Proxy: {config.proxy_url}")

    # Повідомлення про напівавтоматичний режим
    if config.semi_auto:
        print("\n" + "⚠️ " * 20)
        print("👤 НАПІВАВТОМАТИЧНИЙ РЕЖИМ УВІМКНЕНО!")
        print("⚠️ " * 20)
        print("Скрипт буде зупинятися на критичних етапах:")
        print("  • Після заповнення першої сторінки (кнопка Next)")
        print("  • Перед перевіркою email (кнопка Check)")
        print()
        print("Ви зможете:")
        print("  ✅ Перевірити дані перед надсиланням")
        print("  ✅ Вручну пройти капчу якщо потрібно")
        print("  ✅ Обійти детекцію ботів")
        print()
        print("Щоб вимкнути: GMX_SEMI_AUTO=0 у файлі .env")
        print("=" * 80 + "\n")

    logging.getLogger(__name__).info("Using Selenium config: %s", config)

    if config.proxy_url:
        print("🔍 Testing proxy connection...")
        try:
            ensure_proxy_connectivity(config.proxy_url, config.base_url)
            print("✅ Proxy connection successful")
        except ProxyValidationError as exc:
            print(f"❌ Proxy validation failed: {exc}")
            logging.error("Proxy validation failed: %s", exc)
            return 1
    else:
        print("🚫 Proxy disabled")
        logging.info("Proxy disabled via GMX_PROXY_ENABLED=0")

    print("\n👤 Preparing registration data...")
    if args.data_file:
        registration = _load_registration_from_file(args.data_file)
        print(
            f"📁 Loaded from file: {registration.first_name} {registration.last_name}"
        )
    else:
        try:
            registration = generate_registration_data(
                args.locale, use_data_pool=True, mark_as_used=True
            )
            print(
                f"🎲 Generated: {registration.first_name} {registration.last_name} ({registration.birthdate.strftime('%Y-%m-%d')})"
            )
        except ValueError as exc:
            # Handle data pool exhaustion
            print(f"❌ Data pool exhausted: {exc}", file=sys.stderr)
            logging.error("Data pool exhausted: %s", exc)
            return 1

    options = RegistrationOptions(
        skip_submit=args.skip_submit,
        wait_for_manual_confirmation=not args.no_wait,
        success_url_fragment=args.success_url_fragment,
    )

    print("\n🌐 Starting browser and beginning registration...")
    print("=" * 80)

    service = RegistrationService(config)
    try:
        result = service.register(registration, options)
    except ChromeBinaryNotFoundError as exc:
        print(f"❌ BROWSER ERROR: {exc}", file=sys.stderr)
        logging.error("%s", exc)
        return 1

    if args.dump_json:
        print(json.dumps(asdict(registration), default=_json_encode, indent=2))

    if result.success:
        # Get geolocation info (simplified for now - could be enhanced with real geo detection)
        geolocation = "Unknown"
        if config.proxy_url:
            # Extract basic info from proxy URL for tracking
            proxy_info = (
                config.proxy_url.split("@")[-1]
                if "@" in config.proxy_url
                else config.proxy_url
            )
            geolocation = f"Proxy: {proxy_info}"

        try:
            credential_store.save_success(
                registration,
                result,
                geolocation=geolocation,
                proxy_used=config.proxy_url,
            )
        except CredentialStoreError as exc:
            logging.error("Failed to persist credentials: %s", exc)
            print(f"❌ DATABASE ERROR: {exc}", file=sys.stderr)
            return 1

        print("\n" + "=" * 80)
        print("🎉 REGISTRATION COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"👤 Name: {registration.first_name} {registration.last_name}")
        print(f"📧 Email: {result.email_address}")
        print(f"🔐 Password: {registration.password}")
        print(f"📅 Birth Date: {registration.birthdate.strftime('%B %d, %Y')}")
        if config.proxy_url:
            print(f"🌐 Via Proxy: {geolocation}")
        logging.info("Registration succeeded for %s", result.email_address)
        return 0

    # Обробка невдалої реєстрації
    print("\n" + "=" * 80)
    print("💥 REGISTRATION FAILED!")
    print("=" * 80)
    print(f"❌ Target Email: {result.email_address}")
    print(f"🔍 Failure Details: {result.details}")
    print("💡 Suggestion: Try again with different proxy or wait a few minutes")
    print("=" * 80)
    logging.error(
        "Registration incomplete for %s: %s", result.email_address, result.details
    )
    return 1


def _json_encode(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)} is not JSON serialisable")


if __name__ == "__main__":
    raise SystemExit(main())
