#!/usr/bin/env python3
"""
Test script to validate GMX form field mapping with real data from pool.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from app.data_models import generate_registration_data  # noqa: E402
from app.data_pool import get_data_pool_manager  # noqa: E402
from app.utils.form_utils import (
    parse_birthdate_string,
    format_birthdate_for_form,
    format_name_for_form,
)  # noqa: E402


def test_form_field_integration():
    """Test that data from pool works correctly with form field requirements."""

    print("🧪 Testing GMX Form Field Integration\n")

    # Test data pool integration
    pool_manager = get_data_pool_manager()
    stats = pool_manager.get_pool_stats()

    print("📊 Pool Status:")
    print(f"  Available Names: {stats.get('names_available', 0):,}")
    print(f"  Available Cities: {stats.get('cities_available', 0):,}")
    print(f"  Available Security: {stats.get('security_available', 0):,}")

    if stats.get("names_total", 0) == 0:
        print("\n⚠️  No data pools found. Run: python init_data_pool.py")
        return

    print("\n🎯 Testing Form Field Mapping:")
    print("-" * 60)

    # Generate test data
    for i in range(1, 6):
        try:
            data = generate_registration_data(use_data_pool=True)

            # Test name formatting
            formatted_first = format_name_for_form(data.first_name)
            formatted_last = format_name_for_form(data.last_name)

            # Test birthdate conversion
            mm, dd, yyyy = format_birthdate_for_form(data.birthdate)

            print(f"\nSample {i}:")
            print("  📝 Form Fields:")
            print(
                f"     First Name: '{formatted_first}' → input[data-test='first-name-input']"
            )
            print(
                f"     Last Name:  '{formatted_last}' → input[data-test='last-name-input']"
            )
            print(f"     MM: '{mm}' → input[data-test='month']")
            print(f"     DD: '{dd}' → input[data-test='day']")
            print(f"     YYYY: '{yyyy}' → input[data-test='year']")
            print(f"  📧 Email: {data.email_address}")
            print(f"  🔒 Security: {data.security_question} → '{data.security_answer}'")

        except Exception as e:
            print(f"\n❌ Error in sample {i}: {e}")

    print("\n" + "=" * 60)

    # Test direct pool access with birthdate
    print("\n🎲 Direct Pool Access Test:")
    print("-" * 30)

    for i in range(3):
        try:
            # Get raw data from pool (includes birthdate in mm.dd.yyyy format)
            first_name, last_name, birthdate_str, locale = (
                pool_manager.get_random_name()
            )

            # Convert to date object
            birthdate_obj = parse_birthdate_string(birthdate_str)

            # Format for form
            mm, dd, yyyy = format_birthdate_for_form(birthdate_obj)

            print(f"  Raw: {first_name} {last_name} | {birthdate_str} | {locale}")
            print(
                f"  Form: '{format_name_for_form(first_name)}' '{format_name_for_form(last_name)}' | {mm}/{dd}/{yyyy}"
            )
            print()

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("✅ Form field integration test complete!")


if __name__ == "__main__":
    test_form_field_integration()
