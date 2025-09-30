#!/usr/bin/env python3
"""
CLI tool to initialize and manage the data pools for GMX registration.
Run this script to generate 100k+ names, cities, and security answers.
"""

import argparse
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from app.data_pool import DataPoolManager  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(
        description="Initialize and manage data pools for GMX registration"
    )

    parser.add_argument(
        "--names",
        "-n",
        type=int,
        default=100000,
        help="Number of names to generate (default: 100000)",
    )

    parser.add_argument(
        "--stats", action="store_true", help="Show current pool statistics and exit"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all usage flags to make all records available again",
    )

    parser.add_argument(
        "--db-path", type=Path, help="Custom path for the database file"
    )

    args = parser.parse_args()

    # Initialize manager
    manager = DataPoolManager(args.db_path)

    if args.stats:
        stats = manager.get_pool_stats()
        print("\n📊 Current Data Pool Statistics:")
        print(
            f"  Names: {stats.get('names_total', 0):,} total | {stats.get('names_used', 0):,} used | {stats.get('names_available', 0):,} available"
        )
        print(
            f"  Gender: {stats.get('names_mr', 0):,} Mr | {stats.get('names_ms', 0):,} Ms"
        )
        return

    if args.reset:
        print("\n🔄 Resetting usage status...")
        manager.reset_usage_status()

        # Show updated stats
        stats = manager.get_pool_stats()
        print("✅ Usage status reset complete!")
        print(f"  Available Names: {stats.get('names_available', 0):,}")
        print(f"  Mr: {stats.get('names_mr', 0):,} | Ms: {stats.get('names_ms', 0):,}")
        return

    print("\n🚀 Initializing Data Pool...")
    print(f"  Target Names: {args.names:,}")

    if args.db_path:
        print(f"  Database: {args.db_path}")

    try:
        stats = manager.initialize_all_pools(names_count=args.names)

        print("\n✅ Data Pool Initialization Complete!")
        print(f"  Names: {stats.get('names_total', 0):,}")
        print(f"  Mr: {stats.get('names_mr', 0):,}")
        print(f"  Ms: {stats.get('names_ms', 0):,}")

        # Test random generation
        print("\n🎲 Testing Random Generation:")
        name_data = manager.get_random_name()
        print(
            f"  Random Name: {name_data[0]} {name_data[1]} | {name_data[2]} | {name_data[3]}"
        )

    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during generation: {e}")
        logging.exception("Detailed error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
