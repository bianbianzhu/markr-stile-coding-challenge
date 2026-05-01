import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

print("create_async_engine:", inspect.signature(create_async_engine))
print("text:", inspect.signature(text))
