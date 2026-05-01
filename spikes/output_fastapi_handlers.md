# T2.8 FastAPI handlers output

Command:
`uv run python spikes/spike_fastapi_handlers.py`

Output:
```text
/markr → 422 {'error': 'wrong_root', 'message': 'x', 'details': {}}
/unknown → 404 {'error': 'not_found', 'message': 'x', 'details': {'reason': 'unknown_route'}}
/boom → 500 {'error': 'internal_error', 'message': 'internal server error', 'details': {}}
/p/toolong → 422 {'error': 'invalid_path_param', 'message': 'x', 'details': {'raw': '1 validation error:\n  {\'type\': \'string_too_long\', \'loc\': (\'path\', \'x\'), \'msg\': \'String should have at most 3 characters\', \'input\': \'toolong\', \'ctx\': {\'max_length\': 3}}\n\n  File "/Users/tianyili/Learn/ml/markr/spikes/spike_fastapi_handlers.py", line 46, in p\n    GET /p/{x}'}}
POST /markr → 405 {'error': 'method_not_allowed', 'message': 'x', 'details': {}}
```
