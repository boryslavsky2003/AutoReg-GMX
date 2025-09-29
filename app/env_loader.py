from __future__ import annotations

import logging
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

logger = logging.getLogger(__name__)


class EnvFileNotFoundError(RuntimeError):
    pass


def ensure_env_loaded(require_file: bool = True) -> Path | None:
    dotenv_path = find_dotenv(usecwd=True)
    if not dotenv_path:
        if require_file:
            raise EnvFileNotFoundError(
                "Could not locate a .env file. Create one with GMX_PROXY_URL and other settings."
            )
        return None

    load_dotenv(dotenv_path, override=False)
    resolved = Path(dotenv_path).resolve()
    logger.debug("Loaded environment variables from %s", resolved)
    return resolved
