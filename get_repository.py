import os

from repository import TaskRepository


def get_repository() -> TaskRepository:
    """Picks the storage backend from DATABASE_URL. This is the one place
    that changes when swapping backends — every route in main.py is
    unaffected either way."""
    if os.getenv("DATABASE_URL"):
        from postgres_repository import PostgresTaskRepository

        return PostgresTaskRepository(os.environ["DATABASE_URL"])

    from sqlite_repository import SQLiteTaskRepository

    return SQLiteTaskRepository()
