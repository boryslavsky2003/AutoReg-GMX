"""Domain data models and factories for registration flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, get_args
import random

from faker import Faker

GMX_ALLOWED_DOMAINS: tuple[str, ...] = ("gmx.com", "gmx.net", "gmx.us")
SecurityQuestion = Literal[
    "mother_maiden_name",
    "first_pet",
    "birth_city",
]


@dataclass(slots=True)
class RegistrationData:
    """Container for the data required by the GMX signup form."""

    first_name: str
    last_name: str
    email_local_part: str
    email_domain: str
    password: str
    recovery_email: str
    birthdate: date
    security_question: SecurityQuestion
    security_answer: str

    @property
    def email_address(self) -> str:
        return f"{self.email_local_part}@{self.email_domain}"


def generate_registration_data(
    locale: str = "en_US", use_data_pool: bool = True, mark_as_used: bool = True
) -> RegistrationData:
    """Generate realistic registration data from data pool.

    Args:
        locale: Preferred locale for data generation
        use_data_pool: If True, use pre-generated pool of names for variety
        mark_as_used: If True, mark the selected record as used in data pool

    Raises:
        ValueError: If no unused records available in data pool
    """

    # Import here to avoid circular imports
    from .data_pool import get_data_pool_manager

    pool_manager = get_data_pool_manager()

    # Check if we have available records
    stats = pool_manager.get_pool_stats()
    available_count = stats.get("names_available", 0)

    if available_count == 0:
        raise ValueError(
            "❌ No unused records available in data_pool.db! "
            "Please generate more data: python init_data_pool.py --names 10000"
        )

    if use_data_pool:
        try:
            # Get random name from pool and optionally mark as used
            first_name, last_name, birthdate_str, gender = pool_manager.get_random_name(
                mark_as_used=mark_as_used
            )

            # Convert birthdate from "mm.dd.yyyy" string to date object
            from datetime import datetime

            birthdate = datetime.strptime(birthdate_str, "%m.%d.%Y").date()

            # Force Latin-only locales - GMX doesn't accept Cyrillic
            latin_locales = ["en_US", "en_GB", "de_DE", "fr_FR", "es_ES", "it_IT"]
            chosen_locale = random.choice(latin_locales)
        except Exception as exc:
            raise ValueError(f"Failed to get data from pool: {exc}") from exc
    else:
        # Fallback to Faker generation (not recommended for production)
        diverse_locales = [
            "en_US",
            "en_GB",
            "de_DE",
            "fr_FR",
            "es_ES",
            "it_IT",
            "pl_PL",
            "uk_UA",
            "ru_RU",
            "cs_CZ",
            "sv_SE",
            "no_NO",
            "da_DK",
            "fi_FI",
        ]

        chosen_locale = locale if locale != "en_US" else random.choice(diverse_locales)
        faker = Faker(chosen_locale)
        first_name = faker.first_name()
        last_name = faker.last_name()

        # Generate birthdate for fallback case
        age_weights = [0.3, 0.4, 0.2, 0.1]  # 18-25, 26-35, 36-50, 51-65
        age_ranges = [(18, 25), (26, 35), (36, 50), (51, 65)]
        min_age, max_age = random.choices(age_ranges, weights=age_weights)[0]
        birthdate = faker.date_of_birth(minimum_age=min_age, maximum_age=max_age)

    # Create faker for chosen locale (needed for other fields)
    faker = Faker(chosen_locale)

    # More varied email formats
    email_formats = [
        f"{first_name.lower()}.{last_name.lower()}",
        f"{first_name.lower()}{last_name.lower()}",
        f"{first_name.lower()}_{last_name.lower()}",
        f"{first_name[0].lower()}{last_name.lower()}",
        f"{first_name.lower()}{random.randint(1980, 2005)}",
        f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}",
    ]
    base_local_part = random.choice(email_formats)

    # Clean up special characters that might break emails
    base_local_part = base_local_part.replace(" ", "").replace("'", "").replace("-", "")

    # Add random suffix for uniqueness
    suffix_options = [
        str(random.randint(1, 9999)),
        str(random.randint(10, 99)),
        random.choice(["x", "z", "pro", "2024", "2025"]),
        f"{random.randint(1, 99)}{random.choice(['x', 'z', 'pro'])}",
    ]
    suffix = random.choice(suffix_options)
    email_local_part = f"{base_local_part}{suffix}"[:30]

    # Generate strong but varied passwords
    password_patterns = [
        faker.password(
            length=random.randint(12, 20),
            special_chars=True,
            digits=True,
            upper_case=True,
        ),
        f"{faker.word().capitalize()}{random.randint(100, 999)}!",
        f"{faker.first_name()}{faker.last_name()}{random.randint(10, 99)}@",
        f"{random.choice(['Super', 'Cool', 'Best', 'Top'])}{faker.word()}{random.randint(1, 999)}#",
    ]
    password = random.choice(password_patterns)

    # Generate recovery email from different provider
    recovery_providers = [
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "proton.me",
    ]
    recovery_email = f"{faker.user_name()}@{random.choice(recovery_providers)}"

    # More realistic security answers based on question type
    security_question = random.choice(list(get_args(SecurityQuestion)))

    # Generate security answer using Faker (simplified from pool approach)
    if security_question == "mother_maiden_name":
        security_answer = faker.last_name()
    elif security_question == "first_pet":
        pet_names = [
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
            "Ruby",
            "Jack",
        ]
        security_answer = random.choice(pet_names)
    else:  # birth_city
        security_answer = faker.city()

    email_domain = random.choice(GMX_ALLOWED_DOMAINS)

    return RegistrationData(
        first_name=first_name,
        last_name=last_name,
        email_local_part=email_local_part,
        email_domain=email_domain,
        password=password,
        recovery_email=recovery_email,
        birthdate=birthdate,
        security_question=security_question,
        security_answer=security_answer,
    )


@dataclass(slots=True)
class RegistrationResult:
    """Outcome of a registration attempt."""

    email_address: str
    success: bool
    details: str | None = None
