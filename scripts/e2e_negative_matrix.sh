#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:4567}"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

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

assert_envelope() {
  local name="$1"
  local expected_status="$2"
  local expected_error="$3"
  local body_file="$4"
  local status_file="$5"
  local expected_reason="${6:-}"
  local expected_field="${7:-}"

  uv run python - "$name" "$expected_status" "$expected_error" "$body_file" "$status_file" "$expected_reason" "$expected_field" <<'PY'
import json
import sys

name, expected_status, expected_error, body_file, status_file, expected_reason, expected_field = sys.argv[1:]
status = open(status_file, encoding="utf-8").read().strip()
with open(body_file, encoding="utf-8") as f:
    body = json.load(f)

if status != expected_status:
    raise SystemExit(f"{name}: expected HTTP={expected_status}, got HTTP={status}, body={body}")
if body.get("error") != expected_error:
    raise SystemExit(f"{name}: expected error={expected_error}, got {body.get('error')}, body={body}")
if expected_reason and body.get("details", {}).get("reason") != expected_reason:
    raise SystemExit(f"{name}: expected reason={expected_reason}, body={body}")
if expected_field and body.get("details", {}).get("field") != expected_field:
    raise SystemExit(f"{name}: expected field={expected_field}, body={body}")

suffix = ""
if expected_reason:
    suffix += f" reason={expected_reason}"
if expected_field:
    suffix += f" field={expected_field}"
print(f"OK {name}: HTTP={status} error={body.get('error')}{suffix}")
PY
}

run_case() {
  local name="$1"
  local expected_status="$2"
  local expected_error="$3"
  local expected_reason="${4:-}"
  local expected_field="${5:-}"
  shift 5

  local body_file="$TMP_DIR/$name.json"
  local status_file="$TMP_DIR/$name.status"
  curl -sS -o "$body_file" -w "%{http_code}" "$@" >"$status_file"
  assert_envelope "$name" "$expected_status" "$expected_error" "$body_file" "$status_file" "$expected_reason" "$expected_field"
}

wait_health

oversized="$TMP_DIR/oversized.bin"
truncate -s 11000000 "$oversized"

run_case wrong_ct 415 unsupported_media_type "" "" \
  -X POST -H "Content-Type: application/xml" --data-binary "<x/>" "$BASE_URL/import"

run_case wrong_ct_oversized 415 unsupported_media_type "" "" \
  -X POST -H "Content-Type: application/xml" --data-binary @"$oversized" "$BASE_URL/import"

run_case malformed 400 malformed_xml "" "" \
  -X POST -H "Content-Type: text/xml+markr" --data-binary "<oops" "$BASE_URL/import"

run_case wrong_root 422 wrong_root "" "" \
  -X POST -H "Content-Type: text/xml+markr" --data-binary "<other/>" "$BASE_URL/import"

run_case empty_batch 422 empty_batch "" "" \
  -X POST -H "Content-Type: text/xml+markr" --data-binary "<mcq-test-results></mcq-test-results>" "$BASE_URL/import"

run_case invalid_score 422 invalid_score "" "" \
  -X POST -H "Content-Type: text/xml+markr" --data-binary "<mcq-test-results><mcq-test-result><student-number>1</student-number><test-id>T</test-id><summary-marks available=\"0\" obtained=\"0\"/></mcq-test-result></mcq-test-results>" "$BASE_URL/import"

run_case missing_summary_marks 422 cardinality_violation "" summary-marks \
  -X POST -H "Content-Type: text/xml+markr" --data-binary "<mcq-test-results><mcq-test-result><student-number>1</student-number><test-id>T</test-id></mcq-test-result></mcq-test-results>" "$BASE_URL/import"

run_case wrong_method 405 method_not_allowed "" "" \
  -X PUT -H "Content-Type: text/xml+markr" --data-binary "<x/>" "$BASE_URL/import"

run_case invalid_path 422 invalid_path_param "" test_id \
  "$BASE_URL/results/%20%20/aggregate"

run_case unknown_route 404 not_found unknown_route "" \
  "$BASE_URL/nope"

run_case aggregate_no_rows 404 not_found no_matching_rows "" \
  "$BASE_URL/results/NEVERSEEN/aggregate"
