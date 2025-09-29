"""Convenience entrypoint for running AutoReg-GMX via `python main.py`."""

from __future__ import annotations

from app import main as package_main


if __name__ == "__main__":
    raise SystemExit(package_main())
