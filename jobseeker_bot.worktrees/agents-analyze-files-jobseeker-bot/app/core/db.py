import os
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine: AsyncEngine = create_async_engine(DATABASE_URL)
async_session_factory = sessionmaker(engine, expire_on_commit=False)

def get_async_session():
    return async_session_factory()
