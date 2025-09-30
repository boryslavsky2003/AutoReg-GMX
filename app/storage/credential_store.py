"""SQLite-backed storage for GMX registration credentials."""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from ..data_models import RegistrationData, RegistrationResult

logger = logging.getLogger(__name__)


class CredentialStoreError(RuntimeError):
    """Raised when credential persistence fails."""


class CredentialStore:
    """Persist registration credentials to a local SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._initialise_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)

    def _initialise_schema(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gmx_accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        recovery_email TEXT,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        payload_json TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_gmx_accounts_email
                        ON gmx_accounts(email)
                    """
                )
        except sqlite3.Error as exc:
            raise CredentialStoreError(
                f"Failed to initialise credential database at {self._db_path}: {exc}"
            ) from exc

    def save_success(
        self,
        registration: RegistrationData,
        result: RegistrationResult,
    ) -> None:
        """Persist a successful registration, updating duplicates in-place."""

        payload = _registration_payload_json(registration, result)

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO gmx_accounts (email, password, recovery_email, payload_json)
                    VALUES (:email, :password, :recovery_email, :payload_json)
                    ON CONFLICT(email) DO UPDATE SET
                        password=excluded.password,
                        recovery_email=excluded.recovery_email,
                        payload_json=excluded.payload_json,
                        created_at=CURRENT_TIMESTAMP
                    """,
                    {
                        "email": registration.email_address,
                        "password": registration.password,
                        "recovery_email": registration.recovery_email,
                        "payload_json": payload,
                    },
                )
        except sqlite3.Error as exc:
            raise CredentialStoreError(
                f"Failed to store credentials for {registration.email_address}: {exc}"
            ) from exc
        else:
            logger.info(
                "Persisted credentials for %s to %s",
                registration.email_address,
                self._db_path,
            )


def _registration_payload_json(
    registration: RegistrationData,
    result: RegistrationResult,
) -> str:
    payload: dict[str, Any] = {
        "registration": _dataclass_to_serialisable_dict(registration),
        "result": _dataclass_to_serialisable_dict(result),
    }
    return json.dumps(payload, default=_json_default, ensure_ascii=False, indent=2)


def _dataclass_to_serialisable_dict(obj: Any) -> dict[str, Any]:
    mapping = asdict(obj)
    return {key: _json_default(value) for key, value in mapping.items()}


def _json_default(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, dict, str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[arg-type]
    return str(value)
