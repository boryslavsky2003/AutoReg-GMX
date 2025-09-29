"""Domain data models and factories for registration flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, get_args
import random
import string

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


def generate_registration_data(locale: str = "en_US") -> RegistrationData:
    """Generate realistic-but-fake registration data for testing purposes."""

    faker = Faker(locale)
    first_name = faker.first_name()
    last_name = faker.last_name()
    recovery_email = faker.email()
    birthdate = faker.date_of_birth(minimum_age=19, maximum_age=65)

    base_local_part = f"{first_name}.{last_name}".lower().replace(" ", "-")
    suffix = "".join(random.choices(string.digits, k=4))
    email_local_part = f"{base_local_part}{suffix}"[:30]

    password = faker.password(
        length=16, special_chars=True, digits=True, upper_case=True
    )

    security_question = random.choice(list(get_args(SecurityQuestion)))
    security_answer = faker.word().capitalize()

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
