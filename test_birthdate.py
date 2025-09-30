#!/usr/bin/env python3
"""
Test enhanced birthdate filling logic.
"""

import sys
from pathlib import Path
from datetime import date

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.data_models import generate_registration_data  # noqa: E402
from app.config import load_config  # noqa: E402


def test_birthdate_formats():
    """Test different birthdate format scenarios."""

    print("🧪 Testing Enhanced Birthdate Handling\n")

    # Generate test data
    print("1️⃣  Generating Test Registration Data:")
    try:
        reg_data = generate_registration_data(mark_as_used=False)

        print(f"   👤 Name: {reg_data.first_name} {reg_data.last_name}")
        print(f"   📅 Birthdate: {reg_data.birthdate}")
        print(f"   📧 Email: {reg_data.email_address}")

        # Test date formatting
        month_str = f"{reg_data.birthdate.month:02d}"
        day_str = f"{reg_data.birthdate.day:02d}"
        year_str = str(reg_data.birthdate.year)

        print(f"   🗓️  Formatted: Month={month_str}, Day={day_str}, Year={year_str}")

    except Exception as e:
        print(f"   ❌ Data generation failed: {e}")
        return False

    # Test date conversion from pool format
    print("\n2️⃣  Testing Date Pool Format Conversion:")

    # Simulate the pool date format (mm.dd.yyyy)
    pool_date_str = f"{reg_data.birthdate.month:02d}.{reg_data.birthdate.day:02d}.{reg_data.birthdate.year}"
    print(f"   📋 Pool format: {pool_date_str}")

    # Test conversion back to date object
    try:
        from datetime import datetime

        converted_date = datetime.strptime(pool_date_str, "%m.%d.%Y").date()

        print(f"   ✅ Converted back: {converted_date}")
        print(f"   📊 Match original: {converted_date == reg_data.birthdate}")

    except Exception as e:
        print(f"   ❌ Date conversion failed: {e}")
        return False

    # Test form field format requirements
    print("\n3️⃣  Testing Form Field Requirements:")

    test_dates = [
        date(1990, 1, 5),  # Single digit month/day
        date(2000, 12, 31),  # Double digit month/day
        date(1985, 2, 29),  # Leap year (invalid - Feb 29, 1985 doesn't exist)
        date(1988, 2, 29),  # Valid leap year
        date(2005, 11, 15),  # Recent date
    ]

    for test_date in test_dates:
        try:
            month_formatted = f"{test_date.month:02d}"
            day_formatted = f"{test_date.day:02d}"
            year_formatted = str(test_date.year)

            print(
                f"   📅 {test_date} → MM={month_formatted}, DD={day_formatted}, YYYY={year_formatted}"
            )

            # Validate format
            if (
                len(month_formatted) == 2
                and len(day_formatted) == 2
                and len(year_formatted) == 4
            ):
                print(f"      ✅ Format valid")
            else:
                print(f"      ❌ Format invalid")
                return False

        except Exception as e:
            print(f"      ❌ Date formatting error: {e}")

    # Test edge cases
    print("\n4️⃣  Testing Edge Cases:")

    edge_cases = [
        ("Very old person", date(1920, 5, 10)),
        ("Very young person", date(2010, 8, 25)),
        ("New Year", date(1995, 1, 1)),
        ("New Year's Eve", date(1995, 12, 31)),
    ]

    for case_name, test_date in edge_cases:
        month_str = f"{test_date.month:02d}"
        day_str = f"{test_date.day:02d}"
        year_str = str(test_date.year)

        print(f"   🎯 {case_name}: {month_str}/{day_str}/{year_str}")

        # Validate all values are numeric and correct length
        if (
            month_str.isdigit()
            and len(month_str) == 2
            and day_str.isdigit()
            and len(day_str) == 2
            and year_str.isdigit()
            and len(year_str) == 4
        ):
            print(f"      ✅ Edge case handled correctly")
        else:
            print(f"      ❌ Edge case failed")
            return False

    return True


def show_form_integration_tips():
    """Show tips for GMX form integration."""

    print("\n" + "=" * 60)
    print("💡 GMX FORM INTEGRATION TIPS")
    print("=" * 60)

    print("\n🎯 Birthdate Field Selectors Tried (in order):")
    print("   Month:")
    print("   • input[data-test='month']")
    print("   • input[id='bday-month']")
    print("   • input[name='month']")
    print("   • input[autocomplete='bday-month']")
    print("   • .pos-dob--mm")

    print("\n   Day:")
    print("   • input[data-test='day']")
    print("   • input[id='bday-day']")
    print("   • input[name='day']")
    print("   • input[autocomplete='bday-day']")
    print("   • .pos-dob--dd")

    print("\n   Year:")
    print("   • input[data-test='year']")
    print("   • input[id='bday-year']")
    print("   • input[name='year']")
    print("   • input[autocomplete='bday-year']")
    print("   • .pos-dob--yyyy")

    print("\n🔧 Filling Methods Tried (in order):")
    print("   1. Standard Selenium send_keys()")
    print("   2. JavaScript value setting + events")
    print("   3. Manual typing with CTRL+A selection")

    print("\n⚠️  Common Issues & Solutions:")
    print("   • Field not accepting input → Try clicking first")
    print("   • Value not staying → Add small delays")
    print("   • Validation errors → Check MM/DD/YYYY format")
    print("   • Form not recognizing changes → Trigger input/change events")


if __name__ == "__main__":
    print("🎉 ENHANCED BIRTHDATE HANDLING - TEST")
    print("=" * 60)

    success = test_birthdate_formats()

    if success:
        print("\n" + "=" * 60)
        print("✅ ALL BIRTHDATE TESTS PASSED!")
        print("=" * 60)

        show_form_integration_tips()

        print("\n🚀 Ready to test with GMX form:")
        print("   python main.py --skip-submit")

    else:
        print("\n" + "=" * 60)
        print("❌ SOME BIRTHDATE TESTS FAILED!")
        print("=" * 60)

    sys.exit(0 if success else 1)
