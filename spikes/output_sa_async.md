# T2.2 SQLAlchemy async output

Command:
`uv run python spikes/sig_sa_async.py && uv run python spikes/spike_sa_async.py`

Output:
```text
create_async_engine: (url: 'Union[str, URL]', **kw: 'Any') -> 'AsyncEngine'
text: (text: 'str') -> 'TextClause'
url: postgresql+asyncpg://test:test@localhost:65214/test
rows: [('a', 5), ('b', 1)]
stats: {'mean': 3.0, 'p50': 3.0, 'sd': 2.0}
```
