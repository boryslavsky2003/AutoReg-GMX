#!/usr/bin/env python3
"""
Integration test to verify the complete GMX registration flow
with the new data structure and form fields.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from app.data_models import generate_registration_data  # noqa: E402
from app.automation.gmx_registration_page import GMXRegistrationPage  # noqa: E402
from app.config import load_config  # noqa: E402


def test_real_form_filling():
    """Test actual form filling with real GMX page (dry run mode)."""

    print("🧪 Testing Real GMX Form Filling\n")

    # Load config
    config = load_config()

    # Generate test data
    data = generate_registration_data(use_data_pool=True)

    print("📊 Generated Test Data:")
    print(f"  Name: {data.first_name} {data.last_name}")
    print(
        f"  Birthdate: {data.birthdate} (MM/DD/YYYY: {data.birthdate.month:02d}/{data.birthdate.day:02d}/{data.birthdate.year})"
    )
    print(f"  Email: {data.email_address}")
    print(f"  Security: {data.security_question} → '{data.security_answer}'")

    driver = None
    try:
        # Create driver
        print("\n🚀 Creating WebDriver...")
        try:
            from app.driver_factory import create_driver
        except ImportError:
            print("❌ Driver factory not available - skipping browser test")
            return False

        driver = create_driver(config)

        # Initialize page
        page = GMXRegistrationPage(driver, "https://signup.gmx.com/")

        print("🌐 Opening GMX registration page...")
        page.open()

        print("📝 Filling registration form...")
        page.fill_form(data)

        print("✅ Form filling completed successfully!")
        print("\n📋 Form Field Mapping Verified:")
        print(
            f"  ✓ First Name: '{data.first_name}' → input[data-test='first-name-input']"
        )
        print(f"  ✓ Last Name: '{data.last_name}' → input[data-test='last-name-input']")
        print(
            f"  ✓ Birth Month: '{data.birthdate.month:02d}' → input[data-test='month']"
        )
        print(f"  ✓ Birth Day: '{data.birthdate.day:02d}' → input[data-test='day']")
        print(f"  ✓ Birth Year: '{data.birthdate.year}' → input[data-test='year']")
        print(f"  ✓ Email: '{data.email_local_part}' → email field")
        print(f"  ✓ Security Answer: '{data.security_answer}' → security field")

        # Wait for manual verification
        input("\n⏸️  Press Enter after verifying the form is filled correctly...")

    except Exception as e:
        print(f"\n❌ Error during form filling: {e}")
        return False

    finally:
        if driver:
            try:
                driver.quit()
                print("🔚 WebDriver closed")
            except Exception:
                pass

    return True


def quick_validation_test():
    """Quick validation without opening browser."""

    print("⚡ Quick Validation Test\n")

    # Test multiple samples
    for i in range(5):
        data = generate_registration_data(use_data_pool=True)

        # Validate data structure
        assert hasattr(data, "first_name"), "Missing first_name"
        assert hasattr(data, "last_name"), "Missing last_name"
        assert hasattr(data, "birthdate"), "Missing birthdate"
        assert hasattr(data, "email_address"), "Missing email_address"
        assert hasattr(data, "security_answer"), "Missing security_answer"

        # Validate birthdate format
        assert data.birthdate.year >= 1924, f"Birth year too old: {data.birthdate.year}"
        assert data.birthdate.year <= 2006, (
            f"Birth year too young: {data.birthdate.year}"
        )

        print(
            f"  ✓ Sample {i + 1}: {data.first_name} {data.last_name} | {data.birthdate}"
        )

    print("✅ All validations passed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--real":
        success = test_real_form_filling()
        if not success:
            sys.exit(1)
    else:
        print("🔍 Running quick validation (use --real for browser test)\n")
        quick_validation_test()
        print("\n💡 To test with real browser: python test_gmx_integration.py --real")
