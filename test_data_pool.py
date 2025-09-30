#!/usr/bin/env python3
"""
Test script to demonstrate the data pool functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from app.data_models import generate_registration_data  # noqa: E402
from app.data_pool import get_data_pool_manager  # noqa: E402


def test_data_generation():
    """Test data generation with and without pools."""

    print("🧪 Testing Data Generation Systems\n")

    # Test pool manager
    pool_manager = get_data_pool_manager()
    stats = pool_manager.get_pool_stats()

    print("📊 Current Pool Status:")
    print(
        f"  Names: {stats.get('names_total', 0):,} total | {stats.get('names_used', 0):,} used | {stats.get('names_available', 0):,} available"
    )
    print(
        f"  Cities: {stats.get('cities_total', 0):,} total | {stats.get('cities_used', 0):,} used | {stats.get('cities_available', 0):,} available"
    )
    print(
        f"  Security: {stats.get('security_total', 0):,} total | {stats.get('security_used', 0):,} used | {stats.get('security_available', 0):,} available"
    )

    if stats.get("names_total", 0) == 0:
        print("\n⚠️  No data pools found. Run: python init_data_pool.py")
        print("   Falling back to Faker generation...\n")

    print("\n🎲 Sample Generated Data:")
    print("-" * 50)

    # Generate 5 sample registrations
    for i in range(1, 6):
        try:
            data = generate_registration_data(use_data_pool=True)

            print(f"\nSample {i}:")
            print(f"  Name: {data.first_name} {data.last_name}")
            print(f"  Email: {data.email_address}")
            print(f"  Recovery: {data.recovery_email}")
            print(f"  Birth: {data.birthdate}")
            print(f"  Security Q: {data.security_question}")
            print(f"  Security A: {data.security_answer}")

        except Exception as e:
            print(f"\n❌ Error generating sample {i}: {e}")

    # Test marking records as used
    if stats.get("names_total", 0) > 0:
        print("\n🔖 Testing 'mark as used' functionality:")
        print("-" * 50)

        print("Before marking as used:")
        before_stats = pool_manager.get_pool_stats()
        print(f"  Available names: {before_stats.get('names_available', 0)}")

        # Mark some records as used
        for i in range(3):
            name = pool_manager.get_random_name(mark_as_used=True)
            city = pool_manager.get_random_city(mark_as_used=True)
            security = pool_manager.get_random_security_answer(
                "first_pet", mark_as_used=True
            )
            print(
                f"  Marked as used: {name[0]} {name[1]} | {name[2]} | {city} | {security}"
            )

        print("\nAfter marking as used:")
        after_stats = pool_manager.get_pool_stats()
        print(f"  Available names: {after_stats.get('names_available', 0)}")
        print(f"  Available cities: {after_stats.get('cities_available', 0)}")
        print(f"  Available security: {after_stats.get('security_available', 0)}")

    print("\n" + "=" * 50)
    print("✅ Data generation test complete!")


if __name__ == "__main__":
    test_data_generation()
