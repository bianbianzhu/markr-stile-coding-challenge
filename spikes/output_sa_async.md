# T2.2 SQLAlchemy async output

Command:
`uv run python spikes/sig_sa_async.py && uv run python spikes/spike_sa_async.py`

Output:
```text
create_async_engine: (url: 'Union[str, URL]', **kw: 'Any') -> 'AsyncEngine'
text: (text: 'str') -> 'TextClause'
url: postgresql+asyncpg://test:test@localhost:49324/test
initial rows: [('a', 2), ('b', 7), ('c', 4)]
rows: [('a', 5), ('b', 7), ('c', 4)]
stats: {'mean': 5.333333333333333, 'p50': 5.0, 'sd': 1.247219128924647}
```

Duplicate keys within one multi-VALUES UPSERT are not used because ingestion dedups first.
