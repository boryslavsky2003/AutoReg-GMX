"""
Data pool generator and manager for realistic registration data.
Simplified structure: First name | Last name | mm.dd.yyyy | Gender (Mr/Ms) | is_used
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict
import random
import logging

from faker import Faker

logger = logging.getLogger(__name__)


class DataPoolManager:
    """Manages large pools of realistic registration data in SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("app/storage/data_pool.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize the data pool database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Only names_pool table with exact required fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS names_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    birthdate TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    is_used BOOLEAN DEFAULT FALSE,
                    UNIQUE(first_name, last_name, birthdate, gender)
                )
            """)

            # Create indexes for performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_names_gender ON names_pool(gender)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_names_used ON names_pool(is_used)"
            )

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    def get_pool_stats(self) -> Dict[str, int]:
        """Get current pool statistics including used/available counts."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # Names statistics only
            cursor.execute("SELECT COUNT(*) FROM names_pool")
            stats["names_total"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM names_pool WHERE is_used = TRUE")
            stats["names_used"] = cursor.fetchone()[0]
            stats["names_available"] = stats["names_total"] - stats["names_used"]

            # Gender distribution
            cursor.execute("SELECT COUNT(*) FROM names_pool WHERE gender = 'Mr'")
            stats["names_mr"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM names_pool WHERE gender = 'Ms'")
            stats["names_ms"] = cursor.fetchone()[0]

            return stats

    def generate_name_pool(self, target_count: int = 100000, batch_size: int = 1000):
        """Generate a large pool of realistic names with required fields only."""

        # Latin-only locales for GMX compatibility (no Cyrillic)
        locales_weights = [
            ("en_US", 0.30),
            ("en_GB", 0.20),
            ("de_DE", 0.15),
            ("fr_FR", 0.12),
            ("es_ES", 0.10),
            ("it_IT", 0.08),
            ("pl_PL", 0.05),
        ]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check current count
            cursor.execute("SELECT COUNT(*) FROM names_pool")
            current_count = cursor.fetchone()[0]

            if current_count >= target_count:
                logger.info(
                    f"Names pool already has {current_count} records (target: {target_count})"
                )
                return

            needed = target_count - current_count
            logger.info(f"Generating {needed} names to reach target of {target_count}")

            generated = 0
            batch_data = []

            for batch_num in range(0, needed, batch_size):
                batch_data.clear()

                for _ in range(min(batch_size, needed - generated)):
                    # Choose locale based on weights
                    locale = random.choices(
                        [loc for loc, _ in locales_weights],
                        weights=[weight for _, weight in locales_weights],
                    )[0]

                    faker = Faker(locale)

                    # Generate Mr/Ms gender
                    gender = random.choice(["Mr", "Ms"])
                    if gender == "Mr":
                        first_name = faker.first_name_male()
                    else:
                        first_name = faker.first_name_female()

                    last_name = faker.last_name()

                    # Generate birthdate in mm.dd.yyyy format
                    birthdate_obj = faker.date_of_birth(minimum_age=18, maximum_age=65)
                    birthdate = birthdate_obj.strftime("%m.%d.%Y")

                    batch_data.append((first_name, last_name, birthdate, gender))

                # Bulk insert with IGNORE for duplicates
                try:
                    cursor.executemany(
                        "INSERT OR IGNORE INTO names_pool (first_name, last_name, birthdate, gender) VALUES (?, ?, ?, ?)",
                        batch_data,
                    )
                    conn.commit()
                    generated += len(batch_data)

                    if batch_num % (batch_size * 10) == 0:
                        logger.info(f"Generated {generated}/{needed} names...")

                except sqlite3.Error as e:
                    logger.error(f"Error inserting names batch: {e}")

            # Final count
            cursor.execute("SELECT COUNT(*) FROM names_pool")
            final_count = cursor.fetchone()[0]
            logger.info(f"Names pool generation complete: {final_count} total records")

    def get_random_name(self, mark_as_used: bool = False) -> tuple[str, str, str, str]:
        """Get a random name from the pool. Returns (first_name, last_name, birthdate, gender)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # First try to get unused names
            cursor.execute(
                "SELECT id, first_name, last_name, birthdate, gender FROM names_pool WHERE is_used = FALSE ORDER BY RANDOM() LIMIT 1"
            )

            result = cursor.fetchone()
            if result:
                name_id, first_name, last_name, birthdate, gender = result

                # Mark as used if requested
                if mark_as_used:
                    cursor.execute(
                        "UPDATE names_pool SET is_used = TRUE WHERE id = ?", (name_id,)
                    )
                    conn.commit()

                return first_name, last_name, birthdate, gender
            else:
                # If no unused names, fallback to any name or Faker
                cursor.execute(
                    "SELECT first_name, last_name, birthdate, gender FROM names_pool ORDER BY RANDOM() LIMIT 1"
                )

                result = cursor.fetchone()
                if result:
                    return result
                else:
                    # Fallback to Faker if pool is empty
                    faker = Faker("en_US")
                    gender = random.choice(["Mr", "Ms"])
                    if gender == "Mr":
                        first_name = faker.first_name_male()
                    else:
                        first_name = faker.first_name_female()
                    last_name = faker.last_name()
                    birthdate_obj = faker.date_of_birth(minimum_age=18, maximum_age=65)
                    birthdate = birthdate_obj.strftime("%m.%d.%Y")
                    return first_name, last_name, birthdate, gender

    def reset_usage_status(self):
        """Reset all is_used flags to FALSE to reuse all records."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("UPDATE names_pool SET is_used = FALSE")

            conn.commit()
            logger.info("All usage status reset - all records are now available again")

    def get_unused_counts(self) -> Dict[str, int]:
        """Get count of unused records in each pool."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            counts = {}

            cursor.execute("SELECT COUNT(*) FROM names_pool WHERE is_used = FALSE")
            counts["names_unused"] = cursor.fetchone()[0]

            return counts

    def initialize_all_pools(self, names_count: int = 100000):
        """Initialize name pool."""
        logger.info("Starting data pool initialization...")

        self.generate_name_pool(names_count)

        stats = self.get_pool_stats()
        logger.info(f"Data pool initialization complete: {stats}")
        return stats


# Global instance
_data_pool_manager = None


def get_data_pool_manager() -> DataPoolManager:
    """Get the global data pool manager instance."""
    global _data_pool_manager
    if _data_pool_manager is None:
        _data_pool_manager = DataPoolManager()
    return _data_pool_manager
