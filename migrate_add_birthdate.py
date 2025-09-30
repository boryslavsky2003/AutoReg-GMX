#!/usr/bin/env python3
"""
Migration script to add birthdate field to existing names_pool table.
"""

import sqlite3
import sys
from pathlib import Path
from faker import Faker

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def migrate_add_birthdate():
    """Add birthdate column to existing names_pool table and populate it."""

    db_path = Path("app/storage/data_pool.db")
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False

    print(f"🔄 Adding birthdate field to: {db_path}")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Check if birthdate column already exists
        cursor.execute("PRAGMA table_info(names_pool)")
        columns = [row[1] for row in cursor.fetchall()]

        if "birthdate" in columns:
            print("✅ Birthdate column already exists!")
            return True

        print("📝 Adding birthdate column...")

        # Add birthdate column
        cursor.execute("ALTER TABLE names_pool ADD COLUMN birthdate TEXT")

        # Update unique constraint to include birthdate
        print("📝 Updating table structure...")
        cursor.execute("""
            CREATE TABLE names_pool_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                birthdate TEXT NOT NULL,
                locale TEXT NOT NULL,
                gender TEXT,
                is_used BOOLEAN DEFAULT FALSE,
                UNIQUE(first_name, last_name, birthdate)
            )
        """)

        # Get all existing records
        cursor.execute(
            "SELECT id, first_name, last_name, locale, gender, is_used FROM names_pool"
        )
        existing_records = cursor.fetchall()

        print(
            f"📝 Populating birthdate for {len(existing_records)} existing records..."
        )

        # Generate birthdates for existing records
        for record in existing_records:
            record_id, first_name, last_name, locale, gender, is_used = record

            # Generate birthdate in mm.dd.yyyy format
            faker = Faker(locale or "en_US")
            birthdate_obj = faker.date_of_birth(minimum_age=18, maximum_age=65)
            birthdate = birthdate_obj.strftime("%m.%d.%Y")

            # Insert into new table
            cursor.execute(
                """
                INSERT INTO names_pool_new (id, first_name, last_name, birthdate, locale, gender, is_used)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (record_id, first_name, last_name, birthdate, locale, gender, is_used),
            )

        # Replace old table with new one
        cursor.execute("DROP TABLE names_pool")
        cursor.execute("ALTER TABLE names_pool_new RENAME TO names_pool")

        # Recreate indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_names_locale ON names_pool(locale)"
        )

        conn.commit()

        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM names_pool WHERE birthdate IS NOT NULL")
        count_with_birthdate = cursor.fetchone()[0]

        print("✅ Migration completed successfully!")
        print(f"  Records with birthdate: {count_with_birthdate:,}")

        # Show sample records
        cursor.execute(
            "SELECT first_name, last_name, birthdate, locale FROM names_pool LIMIT 5"
        )
        samples = cursor.fetchall()

        print("\n📊 Sample records:")
        for first_name, last_name, birthdate, locale in samples:
            print(f"  {first_name} {last_name} | {birthdate} | {locale}")

        return True


if __name__ == "__main__":
    success = migrate_add_birthdate()
    if success:
        print(
            "\n🎉 Migration complete! Database now has First name | Last name | mm.dd.yyyy | is_used structure."
        )
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
