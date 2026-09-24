"""Embedding vector dimension shared by the ORM model, migration 002 and the
embedding service's response check.

The migration reads this value when it runs, so changing the embedding model
or dimension after the database exists requires recreating the database.
"""

from app.core.config import get_settings

EMBEDDING_DIMENSION = get_settings().embedding_dimension
