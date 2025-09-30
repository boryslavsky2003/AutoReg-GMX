"""
Utility functions for data format conversions and field mapping.
"""

from datetime import date, datetime
from typing import Tuple


def parse_birthdate_string(birthdate_str: str) -> date:
    """Convert birthdate string from mm.dd.yyyy format to date object.

    Args:
        birthdate_str: Date in format "mm.dd.yyyy" (e.g., "03.15.1995")

    Returns:
        date: Python date object

    Raises:
        ValueError: If the string format is invalid
    """
    try:
        return datetime.strptime(birthdate_str, "%m.%d.%Y").date()
    except ValueError as e:
        raise ValueError(
            f"Invalid birthdate format '{birthdate_str}'. Expected mm.dd.yyyy"
        ) from e


def format_birthdate_for_form(birthdate: date) -> Tuple[str, str, str]:
    """Format date object for GMX form fields.

    Args:
        birthdate: Python date object

    Returns:
        Tuple of (MM, DD, YYYY) as strings with zero-padding
    """
    return (f"{birthdate.month:02d}", f"{birthdate.day:02d}", str(birthdate.year))


def validate_birthdate_range(
    birthdate: date, min_age: int = 18, max_age: int = 100
) -> bool:
    """Validate if birthdate is within acceptable age range.

    Args:
        birthdate: Date to validate
        min_age: Minimum age (default: 18)
        max_age: Maximum age (default: 100)

    Returns:
        bool: True if birthdate is valid
    """
    today = date.today()
    age = (
        today.year
        - birthdate.year
        - ((today.month, today.day) < (birthdate.month, birthdate.day))
    )

    return min_age <= age <= max_age


def format_name_for_form(name: str) -> str:
    """Clean and format name for form input.

    Args:
        name: Raw name string

    Returns:
        str: Cleaned name suitable for form input
    """
    # Remove extra whitespace and capitalize properly
    return " ".join(word.capitalize() for word in name.strip().split())
