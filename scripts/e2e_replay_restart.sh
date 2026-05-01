#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:4567}"
TEST_ID="${TEST_ID:-9863}"
SAMPLE="${SAMPLE:-sample_results.xml}"

wait_health() {
  for _ in $(seq 1 30); do
    if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
      return
    fi
    sleep 1
  done
  echo "FAIL health: $BASE_URL/health unavailable" >&2
  exit 1
}

post_sample() {
  local response
  response="$(curl -sS -X POST -H "Content-Type: text/xml+markr" --data-binary @"$SAMPLE" "$BASE_URL/import")"
  if [ "$response" != '{"status":"ok"}' ]; then
    echo "FAIL import: $response" >&2
    exit 1
  fi
  echo "OK import: $response"
}

count_rows() {
  docker compose exec -T db psql -U markr -d markr -tAc "SELECT COUNT(*) FROM test_results WHERE test_id='$TEST_ID'"
}

wait_health
post_sample
count_1="$(count_rows)"
echo "count after first POST: $count_1"

docker compose restart app >/dev/null
wait_health
echo "OK restart: app healthy"

post_sample
count_2="$(count_rows)"
echo "count after replay: $count_2"

if [ "$count_1" != "$count_2" ]; then
  echo "FAIL idempotency: count changed from $count_1 to $count_2" >&2
  exit 1
fi

echo "OK idempotent: count=$count_2"
