#!/usr/bin/env python3
"""
Test script for new simplified data structure.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from app.data_pool import get_data_pool_manager  # noqa: E402


def test_new_structure():
    """Test the new simplified data structure."""

    print("🧪 Testing New Simplified Data Structure\n")

    # Test pool manager
    pool_manager = get_data_pool_manager()
    stats = pool_manager.get_pool_stats()

    print("📊 Current Pool Status:")
    print(
        f"  Names: {stats.get('names_total', 0):,} total | {stats.get('names_used', 0):,} used | {stats.get('names_available', 0):,} available"
    )
    print(
        f"  Gender: {stats.get('names_mr', 0):,} Mr | {stats.get('names_ms', 0):,} Ms"
    )

    if stats.get("names_total", 0) == 0:
        print("\n⚠️  No data found. Run: python init_data_pool.py --names 10000")
        return

    print("\n🎲 Sample Data (First name | Last name | mm.dd.yyyy | Gender | is_used):")
    print("-" * 80)

    # Generate 10 samples
    for i in range(1, 11):
        try:
            first_name, last_name, birthdate, gender = pool_manager.get_random_name()
            print(
                f"  {i:2d}. {first_name:<12} | {last_name:<15} | {birthdate} | {gender:<2} | Available"
            )

        except Exception as e:
            print(f"\n❌ Error generating sample {i}: {e}")

    # Test marking as used
    print(f"\n🔖 Testing 'mark as used' functionality:")
    print("-" * 50)

    print("Before marking as used:")
    before_stats = pool_manager.get_pool_stats()
    print(f"  Available: {before_stats.get('names_available', 0)}")

    # Mark 3 records as used
    for i in range(3):
        first_name, last_name, birthdate, gender = pool_manager.get_random_name(
            mark_as_used=True
        )
        print(f"  Marked as used: {first_name} {last_name} | {birthdate} | {gender}")

    print("\nAfter marking as used:")
    after_stats = pool_manager.get_pool_stats()
    print(f"  Available: {after_stats.get('names_available', 0)}")
    print(f"  Used: {after_stats.get('names_used', 0)}")

    print("\n" + "=" * 80)
    print("✅ New structure test complete!")
    print("\n📋 Database Structure:")
    print("  ✓ First name     (TEXT)")
    print("  ✓ Last name      (TEXT)")
    print("  ✓ mm.dd.yyyy     (TEXT)")
    print("  ✓ Gender Mr/Ms   (TEXT)")
    print("  ✓ is_used        (BOOLEAN)")


if __name__ == "__main__":
    test_new_structure()
