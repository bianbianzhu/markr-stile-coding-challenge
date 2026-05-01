import pytest

from markr.api.errors import MarkrHTTPException
from markr.ingestion.structure import MAX_RECORDS, gate_root_and_count
from markr.ingestion.xml_parser import safe_parse


def _xml(records: int) -> bytes:
    body = b"<mcq-test-results>" + b"<mcq-test-result/>" * records + b"</mcq-test-results>"
    return body


def test_wrong_root_raises_422():
    with pytest.raises(MarkrHTTPException) as ei:
        gate_root_and_count(safe_parse(b"<other/>"))
    assert ei.value.status_code == 422
    assert ei.value.error == "wrong_root"


def test_namespaced_root_rejected():
    body = b'<x:mcq-test-results xmlns:x="http://e/m"></x:mcq-test-results>'
    with pytest.raises(MarkrHTTPException) as ei:
        gate_root_and_count(safe_parse(body))
    assert ei.value.error == "wrong_root"


def test_too_many_records_413():
    with pytest.raises(MarkrHTTPException) as ei:
        gate_root_and_count(safe_parse(_xml(MAX_RECORDS + 1)))
    assert ei.value.status_code == 413
    assert ei.value.error == "record_count_exceeded"
    assert ei.value.details["count"] == MAX_RECORDS + 1


def test_exactly_max_records_allowed():
    rs = gate_root_and_count(safe_parse(_xml(MAX_RECORDS)))
    assert len(rs) == MAX_RECORDS


def test_zero_records_422_empty_batch():
    with pytest.raises(MarkrHTTPException) as ei:
        gate_root_and_count(safe_parse(_xml(0)))
    assert ei.value.status_code == 422
    assert ei.value.error == "empty_batch"
