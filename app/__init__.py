"""AutoReg-GMX package export surface."""

from __future__ import annotations

from .env_loader import ensure_env_loaded
from .main import main

ensure_env_loaded(require_file=False)

__all__ = ["main"]
