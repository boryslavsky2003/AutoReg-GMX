"""Command line entrypoint for the AutoReg-GMX automation."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from typing import Any

from .automation.registration_service import RegistrationOptions, RegistrationService
from .config import SeleniumConfig, load_config
from .data_models import RegistrationData, generate_registration_data
from .driver_factory import ChromeBinaryNotFoundError
from .env_loader import EnvFileNotFoundError, ensure_env_loaded
from .logging_config import configure_logging
from .utils.proxy import ProxyValidationError, ensure_proxy_connectivity


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
        help="HTTP(S) proxy URL to route browser traffic through",
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
        config = replace(config, proxy_url=proxy_arg, use_proxy=True)
    elif not config.use_proxy:
        config = replace(config, proxy_url=None)

    return config


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        ensure_env_loaded()
    except EnvFileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    config = _resolve_config(args)

    if config.use_proxy and not config.proxy_url:
        print(
            "ERROR: GMX_PROXY_URL is missing from .env. Please add your proxy URL.",
            file=sys.stderr,
        )
        return 1

    configure_logging()

    logging.getLogger(__name__).info("Using Selenium config: %s", config)

    if config.proxy_url:
        try:
            ensure_proxy_connectivity(config.proxy_url, config.base_url)
        except ProxyValidationError as exc:
            logging.error("Proxy validation failed: %s", exc)
            return 1
    else:
        logging.info("Proxy disabled via GMX_PROXY_ENABLED=0")

    if args.data_file:
        registration = _load_registration_from_file(args.data_file)
    else:
        registration = generate_registration_data(args.locale)

    options = RegistrationOptions(
        skip_submit=args.skip_submit,
        wait_for_manual_confirmation=not args.no_wait,
        success_url_fragment=args.success_url_fragment,
    )

    service = RegistrationService(config)
    try:
        result = service.register(registration, options)
    except ChromeBinaryNotFoundError as exc:
        logging.error("%s", exc)
        print(exc, file=sys.stderr)
        return 1

    if args.dump_json:
        print(json.dumps(asdict(registration), default=_json_encode, indent=2))

    if result.success:
        logging.info("Registration succeeded for %s", result.email_address)
        return 0

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
