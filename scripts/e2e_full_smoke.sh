#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:4567}"
TEST_ID="${TEST_ID:-9863}"
SAMPLE="${SAMPLE:-sample_results.xml}"
TMP_DIR="$(mktemp -d)"

cleanup() {
  docker compose down -v >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

wait_health() {
  for _ in $(seq 1 60); do
    if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
      return
    fi
    sleep 1
  done
  echo "FAIL health: $BASE_URL/health unavailable" >&2
  docker compose logs app db >&2 || true
  exit 1
}

assert_json_exact() {
  local name="$1"
  local expected="$2"
  local actual="$3"

  if [ "$actual" != "$expected" ]; then
    echo "FAIL $name: expected $expected, got $actual" >&2
    exit 1
  fi
  echo "OK $name: $actual"
}

assert_aggregate() {
  local name="$1"
  local body="$2"

  uv run python - "$name" "$body" <<'PY'
import json
import math
import sys

name = sys.argv[1]
body = json.loads(sys.argv[2])
expected = {
    "mean": 50.80246913580247,
    "stddev": 9.921195359439231,
    "min": 30.0,
    "max": 75.0,
    "p25": 45.0,
    "p50": 50.0,
    "p75": 55.00000000000001,
    "count": 81,
}

if list(body) != list(expected):
    raise SystemExit(f"{name}: key order mismatch: {list(body)}")

for key, expected_value in expected.items():
    actual = body[key]
    if isinstance(expected_value, float):
        if not math.isclose(actual, expected_value, rel_tol=1e-12, abs_tol=1e-12):
            raise SystemExit(f"{name}: {key} expected {expected_value}, got {actual}")
    elif actual != expected_value:
        raise SystemExit(f"{name}: {key} expected {expected_value}, got {actual}")

print(f"OK {name}: aggregate matches sample")
PY
}

assert_error() {
  local name="$1"
  local expected_status="$2"
  local expected_error="$3"
  local body_file="$4"
  local status_file="$5"

  uv run python - "$name" "$expected_status" "$expected_error" "$body_file" "$status_file" <<'PY'
import json
import sys

name, expected_status, expected_error, body_file, status_file = sys.argv[1:]
status = open(status_file, encoding="utf-8").read().strip()
with open(body_file, encoding="utf-8") as f:
    body = json.load(f)

if status != expected_status:
    raise SystemExit(f"{name}: expected HTTP={expected_status}, got HTTP={status}, body={body}")
if body.get("error") != expected_error:
    raise SystemExit(f"{name}: expected error={expected_error}, got {body.get('error')}, body={body}")

print(f"OK {name}: HTTP={status} error={body.get('error')}")
PY
}

post_sample() {
  local response
  response="$(curl -fsS -X POST -H "Content-Type: text/xml+markr" --data-binary @"$SAMPLE" "$BASE_URL/import")"
  assert_json_exact import '{"status":"ok"}' "$response"
}

get_aggregate() {
  curl -fsS "$BASE_URL/results/$TEST_ID/aggregate"
}

count_rows() {
  docker compose exec -T db psql -U markr -d markr -tAc \
    "SELECT COUNT(*) FROM test_results WHERE test_id='$TEST_ID'"
}

assert_count() {
  local expected="$1"
  local actual
  actual="$(count_rows)"
  if [ "$actual" != "$expected" ]; then
    echo "FAIL db_count: expected $expected, got $actual" >&2
    exit 1
  fi
  echo "OK db_count: $actual"
}

docker compose down -v >/dev/null 2>&1 || true
docker compose up --build -d
wait_health
echo "OK health"

health="$(curl -fsS "$BASE_URL/health")"
assert_json_exact health '{"status":"ok"}' "$health"

post_sample
first_aggregate="$(get_aggregate)"
assert_aggregate aggregate_after_first "$first_aggregate"
assert_count 81

post_sample
second_aggregate="$(get_aggregate)"
assert_aggregate aggregate_after_replay "$second_aggregate"
assert_count 81
assert_json_exact replay_aggregate_stable "$first_aggregate" "$second_aggregate"

docker compose restart app >/dev/null
wait_health
restart_aggregate="$(get_aggregate)"
assert_aggregate aggregate_after_restart "$restart_aggregate"
assert_json_exact restart_aggregate_stable "$first_aggregate" "$restart_aggregate"

oversized="$TMP_DIR/oversized.bin"
truncate -s 11000000 "$oversized"
body_file="$TMP_DIR/body_too_large.json"
status_file="$TMP_DIR/body_too_large.status"
curl -sS -o "$body_file" -w "%{http_code}" \
  -X POST -H "Content-Type: text/xml+markr" --data-binary @"$oversized" "$BASE_URL/import" \
  >"$status_file"
assert_error body_too_large 413 body_too_large "$body_file" "$status_file"

BASE_URL="$BASE_URL" scripts/e2e_negative_matrix.sh

echo "OK full smoke"
