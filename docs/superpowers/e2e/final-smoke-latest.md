# Final Smoke Latest Output

Commands:

```bash
docker compose down -v
docker compose up --build -d
sleep 8
curl -sS http://localhost:4567/health
curl -sS -X POST -H 'Content-Type: text/xml+markr' --data-binary @sample_results.xml http://localhost:4567/import
curl -sS http://localhost:4567/results/9863/aggregate
docker compose down
uv run ruff check .
uv run ruff format --check .
uv run mypy src/markr
uv run pytest
```

Docker smoke output:

```text
health: {"status":"ok"}
import: {"status":"ok"}
aggregate: {"mean":50.80246913580247,"stddev":9.921195359439231,"min":30.0,"max":75.0,"p25":45.0,"p50":50.0,"p75":55.00000000000001,"count":81}
```

Local sweep summary:

```text
uv run ruff check .              -> All checks passed!
uv run ruff format --check .     -> 52 files already formatted
uv run mypy src/markr            -> Success: no issues found in 21 source files
uv run pytest                    -> 81 passed
```
