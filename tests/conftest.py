import pytest
import os
import aiosqlite
from config import DB_PATH
from database.core import init_database

@pytest.fixture(autouse=True)
async def setup_test_db():
    """Initializes the database schema before each test run."""
    await init_database()
    yield
    # Clean up test database file if created
    if os.path.exists(DB_PATH) and "test" in DB_PATH:
        try:
            os.remove(DB_PATH)
        except OSError:
            pass