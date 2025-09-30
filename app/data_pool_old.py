"""
Data pool generator and manager for realistic registration data.
Creates and manages large pools of realistic names, cities, and other data.
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

            # Names pool - simplified structure
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

            # Only names_pool table - no other tables needed

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
        """Generate a large pool of realistic names."""

        # Diverse locales with weights (more English/European names)
        locales_weights = [
            ("en_US", 0.25),
            ("en_GB", 0.15),
            ("de_DE", 0.12),
            ("fr_FR", 0.10),
            ("es_ES", 0.08),
            ("it_IT", 0.06),
            ("pl_PL", 0.05),
            ("uk_UA", 0.05),
            ("ru_RU", 0.04),
            ("cs_CZ", 0.03),
            ("sv_SE", 0.02),
            ("no_NO", 0.02),
            ("da_DK", 0.02),
            ("fi_FI", 0.01),
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

                    # Generate both Mr and Ms for variety
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

    def generate_cities_pool(self, target_count: int = 50000, batch_size: int = 1000):
        """Generate a large pool of realistic cities."""

        locales_weights = [
            ("en_US", 0.3),
            ("en_GB", 0.1),
            ("de_DE", 0.15),
            ("fr_FR", 0.1),
            ("es_ES", 0.08),
            ("it_IT", 0.07),
            ("pl_PL", 0.05),
            ("uk_UA", 0.05),
            ("ru_RU", 0.05),
            ("cs_CZ", 0.03),
            ("sv_SE", 0.02),
        ]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM cities_pool")
            current_count = cursor.fetchone()[0]

            if current_count >= target_count:
                logger.info(f"Cities pool already has {current_count} records")
                return

            needed = target_count - current_count
            logger.info(f"Generating {needed} cities...")

            generated = 0

            for batch_num in range(0, needed, batch_size):
                batch_data = []

                for _ in range(min(batch_size, needed - generated)):
                    locale = random.choices(
                        [loc for loc, _ in locales_weights],
                        weights=[weight for _, weight in locales_weights],
                    )[0]

                    faker = Faker(locale)
                    city_name = faker.city()
                    country = faker.country()

                    batch_data.append((city_name, country, locale))

                try:
                    cursor.executemany(
                        "INSERT OR IGNORE INTO cities_pool (city_name, country, locale) VALUES (?, ?, ?)",
                        batch_data,
                    )
                    conn.commit()
                    generated += len(batch_data)

                    if batch_num % (batch_size * 5) == 0:
                        logger.info(f"Generated {generated}/{needed} cities...")

                except sqlite3.Error as e:
                    logger.error(f"Error inserting cities batch: {e}")

            cursor.execute("SELECT COUNT(*) FROM cities_pool")
            final_count = cursor.fetchone()[0]
            logger.info(f"Cities pool generation complete: {final_count} total records")

    def generate_security_answers_pool(self, target_per_type: int = 10000):
        """Generate pools of realistic security question answers."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Pet names pool
            logger.info("Generating pet names...")
            pet_names = []
            faker = Faker("en_US")

            # Common pet names + generated ones
            common_pets = [
                "Buddy",
                "Max",
                "Charlie",
                "Lucy",
                "Bella",
                "Rocky",
                "Daisy",
                "Luna",
                "Milo",
                "Coco",
                "Rex",
                "Princess",
                "Shadow",
                "Tiger",
                "Fluffy",
                "Oscar",
                "Sophie",
                "Jack",
                "Molly",
                "Teddy",
                "Lily",
                "Bear",
                "Rosie",
                "Toby",
            ]

            # Add common names
            for name in common_pets:
                pet_names.append(("first_pet", name, "en_US"))

            # Generate more pet names
            for _ in range(target_per_type - len(common_pets)):
                pet_name = faker.first_name()
                pet_names.append(("first_pet", pet_name, "en_US"))

            # Maiden names (just use last names from different locales)
            logger.info("Generating maiden names...")
            maiden_names = []
            for locale in [
                "en_US",
                "en_GB",
                "de_DE",
                "fr_FR",
                "es_ES",
                "it_IT",
                "pl_PL",
            ]:
                faker_locale = Faker(locale)
                for _ in range(target_per_type // 7):  # Distribute across locales
                    maiden_name = faker_locale.last_name()
                    maiden_names.append(("mother_maiden_name", maiden_name, locale))

            # Birth cities (use cities from cities_pool or generate)
            logger.info("Generating birth cities...")
            birth_cities = []
            for locale in ["en_US", "en_GB", "de_DE", "fr_FR", "es_ES"]:
                faker_locale = Faker(locale)
                for _ in range(target_per_type // 5):
                    city = faker_locale.city()
                    birth_cities.append(("birth_city", city, locale))

            # Insert all data
            all_answers = pet_names + maiden_names + birth_cities

            try:
                cursor.executemany(
                    "INSERT OR IGNORE INTO security_answers_pool (question_type, answer, locale) VALUES (?, ?, ?)",
                    all_answers,
                )
                conn.commit()

                # Get final counts
                for q_type in ["first_pet", "mother_maiden_name", "birth_city"]:
                    cursor.execute(
                        "SELECT COUNT(*) FROM security_answers_pool WHERE question_type = ?",
                        (q_type,),
                    )
                    count = cursor.fetchone()[0]
                    logger.info(f"Security answers for '{q_type}': {count} records")

            except sqlite3.Error as e:
                logger.error(f"Error inserting security answers: {e}")

    def get_random_name(
        self, locale: Optional[str] = None, mark_as_used: bool = False
    ) -> tuple[str, str, str, str]:
        """Get a random name from the pool. Returns (first_name, last_name, birthdate, locale)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # First try to get unused names
            if locale:
                cursor.execute(
                    "SELECT id, first_name, last_name, birthdate, locale FROM names_pool WHERE locale = ? AND is_used = FALSE ORDER BY RANDOM() LIMIT 1",
                    (locale,),
                )
            else:
                cursor.execute(
                    "SELECT id, first_name, last_name, birthdate, locale FROM names_pool WHERE is_used = FALSE ORDER BY RANDOM() LIMIT 1"
                )

            result = cursor.fetchone()
            if result:
                name_id, first_name, last_name, birthdate, actual_locale = result

                # Mark as used if requested
                if mark_as_used:
                    cursor.execute(
                        "UPDATE names_pool SET is_used = TRUE WHERE id = ?", (name_id,)
                    )
                    conn.commit()

                return first_name, last_name, birthdate, actual_locale
            else:
                # If no unused names, fallback to any name or Faker
                if locale:
                    cursor.execute(
                        "SELECT first_name, last_name, birthdate, locale FROM names_pool WHERE locale = ? ORDER BY RANDOM() LIMIT 1",
                        (locale,),
                    )
                else:
                    cursor.execute(
                        "SELECT first_name, last_name, birthdate, locale FROM names_pool ORDER BY RANDOM() LIMIT 1"
                    )

                result = cursor.fetchone()
                if result:
                    return result
                else:
                    # Fallback to Faker if pool is empty
                    faker = Faker(locale or "en_US")
                    birthdate_obj = faker.date_of_birth(minimum_age=18, maximum_age=65)
                    birthdate = birthdate_obj.strftime("%m.%d.%Y")
                    return (
                        faker.first_name(),
                        faker.last_name(),
                        birthdate,
                        locale or "en_US",
                    )

    def get_random_city(
        self, locale: Optional[str] = None, mark_as_used: bool = False
    ) -> str:
        """Get a random city from the pool."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # First try to get unused cities
            if locale:
                cursor.execute(
                    "SELECT id, city_name FROM cities_pool WHERE locale = ? AND is_used = FALSE ORDER BY RANDOM() LIMIT 1",
                    (locale,),
                )
            else:
                cursor.execute(
                    "SELECT id, city_name FROM cities_pool WHERE is_used = FALSE ORDER BY RANDOM() LIMIT 1"
                )

            result = cursor.fetchone()
            if result:
                city_id, city_name = result

                # Mark as used if requested
                if mark_as_used:
                    cursor.execute(
                        "UPDATE cities_pool SET is_used = TRUE WHERE id = ?", (city_id,)
                    )
                    conn.commit()

                return city_name
            else:
                # Fallback to any city or Faker
                if locale:
                    cursor.execute(
                        "SELECT city_name FROM cities_pool WHERE locale = ? ORDER BY RANDOM() LIMIT 1",
                        (locale,),
                    )
                else:
                    cursor.execute(
                        "SELECT city_name FROM cities_pool ORDER BY RANDOM() LIMIT 1"
                    )

                result = cursor.fetchone()
                if result:
                    return result[0]
                else:
                    faker = Faker(locale or "en_US")
                    return faker.city()

    def get_random_security_answer(
        self,
        question_type: str,
        locale: Optional[str] = None,
        mark_as_used: bool = False,
    ) -> str:
        """Get a random security answer for the given question type."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # First try to get unused answers
            if locale:
                cursor.execute(
                    "SELECT id, answer FROM security_answers_pool WHERE question_type = ? AND locale = ? AND is_used = FALSE ORDER BY RANDOM() LIMIT 1",
                    (question_type, locale),
                )
            else:
                cursor.execute(
                    "SELECT id, answer FROM security_answers_pool WHERE question_type = ? AND is_used = FALSE ORDER BY RANDOM() LIMIT 1",
                    (question_type,),
                )

            result = cursor.fetchone()
            if result:
                answer_id, answer = result

                # Mark as used if requested
                if mark_as_used:
                    cursor.execute(
                        "UPDATE security_answers_pool SET is_used = TRUE WHERE id = ?",
                        (answer_id,),
                    )
                    conn.commit()

                return answer
            else:
                # Try any answer (used or unused)
                if locale:
                    cursor.execute(
                        "SELECT answer FROM security_answers_pool WHERE question_type = ? AND locale = ? ORDER BY RANDOM() LIMIT 1",
                        (question_type, locale),
                    )
                else:
                    cursor.execute(
                        "SELECT answer FROM security_answers_pool WHERE question_type = ? ORDER BY RANDOM() LIMIT 1",
                        (question_type,),
                    )

                result = cursor.fetchone()
                if result:
                    return result[0]
                else:
                    # Fallback logic
                    faker = Faker(locale or "en_US")
                    if question_type == "mother_maiden_name":
                        return faker.last_name()
                    elif question_type == "first_pet":
                        return random.choice(["Buddy", "Max", "Luna", "Bella"])
                    else:  # birth_city
                        return faker.city()

    def initialize_all_pools(
        self,
        names_count: int = 100000,
        cities_count: int = 50000,
        security_count: int = 10000,
    ):
        """Initialize all data pools in one go."""
        logger.info("Starting data pool initialization...")

        self.generate_name_pool(names_count)
        self.generate_cities_pool(cities_count)
        self.generate_security_answers_pool(security_count)

        stats = self.get_pool_stats()
        logger.info(f"Data pool initialization complete: {stats}")
        return stats

    def reset_usage_status(self):
        """Reset all is_used flags to FALSE to reuse all records."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("UPDATE names_pool SET is_used = FALSE")
            cursor.execute("UPDATE cities_pool SET is_used = FALSE")
            cursor.execute("UPDATE security_answers_pool SET is_used = FALSE")

            conn.commit()
            logger.info("All usage status reset - all records are now available again")

    def get_unused_counts(self) -> Dict[str, int]:
        """Get count of unused records in each pool."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            counts = {}

            cursor.execute("SELECT COUNT(*) FROM names_pool WHERE is_used = FALSE")
            counts["names_unused"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM cities_pool WHERE is_used = FALSE")
            counts["cities_unused"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM security_answers_pool WHERE is_used = FALSE"
            )
            counts["security_unused"] = cursor.fetchone()[0]

            return counts


# Global instance
_data_pool_manager = None


def get_data_pool_manager() -> DataPoolManager:
    """Get the global data pool manager instance."""
    global _data_pool_manager
    if _data_pool_manager is None:
        _data_pool_manager = DataPoolManager()
    return _data_pool_manager
