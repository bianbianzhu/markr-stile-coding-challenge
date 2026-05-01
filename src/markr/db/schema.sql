CREATE TABLE IF NOT EXISTS test_results (
  test_id          TEXT NOT NULL,
  student_number   TEXT NOT NULL,
  marks_available  INT  NOT NULL CHECK (marks_available > 0),
  marks_obtained   INT  NOT NULL CHECK (marks_obtained  >= 0
                                    AND marks_obtained <= marks_available),
  first_name       TEXT,
  last_name        TEXT,
  scanned_on       TIMESTAMPTZ,
  PRIMARY KEY (test_id, student_number)
);
