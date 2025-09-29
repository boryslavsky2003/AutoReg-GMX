"""Application configuration helpers for the AutoReg-GMX project."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .env_loader import ensure_env_loaded

ensure_env_loaded(require_file=False)


@dataclass(frozen=True)
class SeleniumConfig:
    """Container for Selenium runtime options."""

    base_url: str
    headless: bool
    window_width: int
    window_height: int
    implicit_wait_s: int
    page_load_timeout_s: int
    downloads_dir: Path
    proxy_url: str | None
    use_proxy: bool


def _str_to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> SeleniumConfig:
    """Build a SeleniumConfig instance using environment variables with fallbacks."""

    downloads_dir = Path(
        os.getenv("GMX_DOWNLOAD_DIR", Path.cwd() / "downloads")
    ).expanduser()
    downloads_dir.mkdir(parents=True, exist_ok=True)

    proxy_enabled = _str_to_bool(os.getenv("GMX_PROXY_ENABLED"), True)
    proxy_env = os.getenv("GMX_PROXY_URL")
    proxy_url = proxy_env.strip() if proxy_env and proxy_env.strip() else None
    if not proxy_enabled:
        proxy_url = None

    return SeleniumConfig(
        base_url=os.getenv(
            "GMX_BASE_URL", "https://signup.gmx.com/#.1559516-header-signup1-1"
        ),
        headless=_str_to_bool(os.getenv("GMX_HEADLESS"), True),
        window_width=int(os.getenv("GMX_WINDOW_WIDTH", "1920")),
        window_height=int(os.getenv("GMX_WINDOW_HEIGHT", "1080")),
        implicit_wait_s=int(os.getenv("GMX_IMPLICIT_WAIT", "5")),
        page_load_timeout_s=int(os.getenv("GMX_PAGE_LOAD_TIMEOUT", "30")),
        downloads_dir=downloads_dir.resolve(),
        proxy_url=proxy_url,
        use_proxy=proxy_enabled,
    )
