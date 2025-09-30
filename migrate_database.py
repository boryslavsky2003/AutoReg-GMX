#!/usr/bin/env python3
"""
Migration script to update existing database schema from created_at to is_used fields.
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def migrate_database(db_path: Path):
    """Migrate database schema from created_at to is_used."""

    print(f"🔄 Migrating database: {db_path}")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Check if migration is needed
        cursor.execute("PRAGMA table_info(names_pool)")
        columns = [col[1] for col in cursor.fetchall()]

        if "is_used" in columns:
            print("✅ Database already migrated!")
            return

        print("📝 Adding is_used columns...")

        try:
            # Add is_used columns to all tables
            cursor.execute(
                "ALTER TABLE names_pool ADD COLUMN is_used BOOLEAN DEFAULT FALSE"
            )
            cursor.execute(
                "ALTER TABLE cities_pool ADD COLUMN is_used BOOLEAN DEFAULT FALSE"
            )
            cursor.execute(
                "ALTER TABLE security_answers_pool ADD COLUMN is_used BOOLEAN DEFAULT FALSE"
            )

            conn.commit()
            print("✅ Migration completed successfully!")

            # Show updated schema
            cursor.execute("SELECT COUNT(*) FROM names_pool")
            names_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM cities_pool")
            cities_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM security_answers_pool")
            security_count = cursor.fetchone()[0]

            print("\n📊 Updated Database Statistics:")
            print(f"  Names: {names_count:,} (all available)")
            print(f"  Cities: {cities_count:,} (all available)")
            print(f"  Security Answers: {security_count:,} (all available)")

        except sqlite3.Error as e:
            print(f"❌ Migration failed: {e}")
            raise


def main():
    db_path = Path("app/storage/data_pool.db")

    if not db_path.exists():
        print("⚠️  Database not found. Run init_data_pool.py first.")
        return

    migrate_database(db_path)
    print("\n🎉 Migration complete! You can now use the new is_used functionality.")


if __name__ == "__main__":
    main()
