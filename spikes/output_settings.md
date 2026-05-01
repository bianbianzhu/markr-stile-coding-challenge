# T2.5 pydantic-settings output

Command:
`uv run python spikes/spike_settings.py`

Output:
```text
loaded: {'DATABASE_URL': 'postgresql+asyncpg://x:x@h/db', 'LOG_LEVEL': 'INFO', 'WRITE_POOL_SIZE': 10, 'WRITE_POOL_OVERFLOW': 20, 'READ_POOL_SIZE': 5, 'READ_POOL_OVERFLOW': 10}
missing raises: ValidationError
```
