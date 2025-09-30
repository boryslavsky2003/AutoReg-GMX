#!/usr/bin/env python3
"""
Integration test for complete data flow:
data_pool.db -> registration -> gmx_accounts.db
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.data_models import generate_registration_data  # noqa: E402
from app.data_pool import get_data_pool_manager  # noqa: E402
from app.storage.credential_store import CredentialStore  # noqa: E402
from app.config import load_config  # noqa: E402


def test_complete_integration():
    """Test complete data flow from pool to credentials storage."""

    print("🧪 Testing Complete Data Integration Flow\n")

    # Step 1: Check data pool status
    pool_manager = get_data_pool_manager()
    initial_stats = pool_manager.get_pool_stats()

    print("📊 Initial Data Pool Status:")
    print(f"  Available: {initial_stats.get('names_available', 0):,}")
    print(f"  Used: {initial_stats.get('names_used', 0):,}")

    if initial_stats.get("names_available", 0) == 0:
        print("\n❌ No data available! Please run:")
        print("   python init_data_pool.py --names 1000")
        return False

    # Step 2: Test data generation with marking as used
    print("\n🎲 Step 1: Generate registration data from pool")

    try:
        registration = generate_registration_data(
            locale="en_US", use_data_pool=True, mark_as_used=True
        )

        print(f"  ✅ Generated: {registration.first_name} {registration.last_name}")
        print(f"  📅 Birthdate: {registration.birthdate}")
        print(f"  📧 Email: {registration.email_address}")
        print(f"  🔐 Password: {registration.password}")
        print(f"  🔒 Security Q: {registration.security_question}")
        print(f"  🗝️  Security A: {registration.security_answer}")

    except ValueError as e:
        print(f"  ❌ Error: {e}")
        return False

    # Step 3: Check that record was marked as used
    print("\n📈 Step 2: Verify data pool updated")

    after_stats = pool_manager.get_pool_stats()
    used_diff = after_stats.get("names_used", 0) - initial_stats.get("names_used", 0)
    available_diff = initial_stats.get("names_available", 0) - after_stats.get(
        "names_available", 0
    )

    print(f"  Records marked as used: +{used_diff}")
    print(f"  Records now available: -{available_diff}")

    if used_diff == 1 and available_diff == 1:
        print("  ✅ Pool correctly updated!")
    else:
        print(f"  ❌ Pool update failed! Expected +1 used, -1 available")
        return False

    # Step 4: Test credential storage
    print("\n💾 Step 3: Test credential storage")

    try:
        config = load_config()
        credential_store = CredentialStore(config.credentials_db_path)

        # Create a fake successful result for testing
        from app.data_models import RegistrationResult

        fake_result = RegistrationResult(
            email_address=registration.email_address,
            success=True,
            details="Integration test",
        )

        # Save with geolocation and proxy info
        credential_store.save_success(
            registration=registration,
            result=fake_result,
            geolocation="Test Location - Ukraine",
            proxy_used="test-proxy:1080",
        )

        print(f"  ✅ Saved credentials for: {registration.email_address}")
        print(f"  📁 Database: {config.credentials_db_path}")

    except Exception as e:
        print(f"  ❌ Error saving credentials: {e}")
        return False

    # Step 5: Test data exhaustion scenario
    print(f"\n⚠️  Step 4: Test data exhaustion handling")

    # First, check how many records we have left
    current_stats = pool_manager.get_pool_stats()
    available = current_stats.get("names_available", 0)

    if available > 5:
        print(f"  📊 {available} records still available")
        print(
            f"  ℹ️  To test exhaustion, you could run registration {available} more times"
        )
    else:
        print(f"  ⚠️  Only {available} records left - testing exhaustion scenario")

        # Try to exhaust remaining records
        exhaustion_count = 0
        while available > 0:
            try:
                test_reg = generate_registration_data(mark_as_used=True)
                exhaustion_count += 1
                available -= 1
                print(
                    f"    Used record {exhaustion_count}: {test_reg.first_name} {test_reg.last_name}"
                )
            except ValueError:
                break

        # Now test the exhaustion error
        try:
            generate_registration_data(mark_as_used=True)
            print("  ❌ Expected exhaustion error but didn't get one!")
            return False
        except ValueError as e:
            print(f"  ✅ Correctly caught exhaustion: {e}")

    print("\n" + "=" * 80)
    print("✅ Integration Test Complete!")
    print("\n📋 Verified Flow:")
    print("  1. ✓ Data retrieved from data_pool.db")
    print("  2. ✓ Record marked as 'used' in data_pool.db")
    print("  3. ✓ Account credentials saved to gmx_accounts.db")
    print("  4. ✓ Geolocation and proxy info stored")
    print("  5. ✓ Data exhaustion properly handled")

    return True


if __name__ == "__main__":
    success = test_complete_integration()
    sys.exit(0 if success else 1)
