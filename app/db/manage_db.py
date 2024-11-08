from sqlalchemy.ext.asyncio import AsyncEngine
import asyncio
from typing import Optional
from sqlalchemy import text
from app.models.models import Base
from app.core.config import engine, init_db


async def drop_all_tables_async(engine_instance: Optional[AsyncEngine] = None) -> None:
    current_engine = engine_instance or engine

    try:
        async with current_engine.begin() as conn:
            # Disable foreign key checks
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

            # Drop all tables
            await conn.run_sync(Base.metadata.drop_all)

            # Re-enable foreign key checks
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

        print("All tables successfully dropped")
    except Exception as e:
        print(f"Error dropping tables: {str(e)}")
        raise


async def create_tables_async(engine_instance: Optional[AsyncEngine] = None) -> None:
    """Create all tables defined in the models"""
    current_engine = engine_instance or engine

    try:
        async with current_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("All tables successfully created")
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        raise


async def verify_tables_async(engine_instance: Optional[AsyncEngine] = None) -> None:
    """Verify that all required tables were created correctly"""
    current_engine = engine_instance or engine
    expected_tables = {'users', 'shops', 'users_shops', 'invoices', 'invoice_items'}

    try:
        async with current_engine.connect() as conn:
            # Get list of all tables in the database
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :schema AND table_type = 'BASE TABLE';"
            ), {"schema": "faragjdatabase"})

            existing_tables = {row[0] for row in result.fetchall()}

            # Check if all expected tables exist
            missing_tables = expected_tables - existing_tables
            if missing_tables:
                print(f"Warning: Missing tables: {missing_tables}")
            else:
                print("All required tables are present")

            # Print table details
            print("\nTable details:")
            for table in existing_tables:
                result = await conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table;"
                ), {"schema": "faragjdatabase", "table": table})
                column_count = result.scalar()
                print(f"- {table}: {column_count} columns")

    except Exception as e:
        print(f"Error verifying tables: {str(e)}")
        raise


async def initialize_database() -> None:
    """Initialize the database with all required tables"""
    try:
        print("Starting database initialization...")

        # Initialize the database connection
        await init_db()

        # Drop existing tables
        print("\nDropping existing tables...")
        await drop_all_tables_async()

        # Create new tables
        print("\nCreating tables...")
        await create_tables_async()

        # Verify tables
        print("\nVerifying database structure...")
        await verify_tables_async()

        print("\nDatabase initialization completed successfully!")

    except Exception as e:
        print(f"\nError during database initialization: {str(e)}")
        raise
    finally:
        await engine.dispose()


# Main execution
if __name__ == "__main__":
    try:
        asyncio.run(initialize_database())
    except KeyboardInterrupt:
        print("\nDatabase initialization cancelled by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        exit(1)