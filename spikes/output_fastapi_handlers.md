# T2.8 FastAPI handlers output

Command:
`uv run python spikes/spike_fastapi_handlers.py`

Output:
```text
/markr -> 422 {'error': 'wrong_root', 'message': 'x', 'details': {}}
/unknown -> 404 {'error': 'not_found', 'message': 'x', 'details': {'reason': 'unknown_route'}}
/boom -> 500 {'error': 'internal_error', 'message': 'internal server error', 'details': {}}
/p/toolong -> 422 {'error': 'invalid_path_param', 'message': 'x', 'details': {'raw': '1 validation error: ... string_too_long ... max_length ...'}}
POST /markr -> 405 {'error': 'method_not_allowed', 'message': 'x', 'details': {}}
```
