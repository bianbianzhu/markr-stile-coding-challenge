# Negative Matrix E2E Latest Output

Command:

```bash
scripts/e2e_negative_matrix.sh
```

Output:

```text
OK wrong_ct: HTTP=415 error=unsupported_media_type
OK wrong_ct_oversized: HTTP=415 error=unsupported_media_type
OK malformed: HTTP=400 error=malformed_xml
OK wrong_root: HTTP=422 error=wrong_root
OK empty_batch: HTTP=422 error=empty_batch
OK invalid_score: HTTP=422 error=invalid_score
OK missing_summary_marks: HTTP=422 error=cardinality_violation field=summary-marks
OK wrong_method: HTTP=405 error=method_not_allowed
OK invalid_path: HTTP=422 error=invalid_path_param field=test_id
OK unknown_route: HTTP=404 error=not_found reason=unknown_route
OK aggregate_no_rows: HTTP=404 error=not_found reason=no_matching_rows
```
