from datetime import datetime, timedelta, timezone
from xml.etree.ElementTree import Element, fromstring

import pytest

from markr.api.errors import MarkrHTTPException
from markr.ingestion.validator import RawRecord, validate_record


def parse(xml: str) -> Element:
    return fromstring(xml)


def good_xml() -> Element:
    return parse(
        """
    <mcq-test-result scanned-on="2017-12-04T12:12:10+11:00">
      <first-name>Jane</first-name>
      <last-name>Austen</last-name>
      <student-number>521585128</student-number>
      <test-id>1234</test-id>
      <summary-marks available="20" obtained="13"/>
    </mcq-test-result>
    """.strip()
    )


def test_happy_path():
    r = validate_record(good_xml())
    assert r == RawRecord(
        test_id="1234",
        student_number="521585128",
        marks_available=20,
        marks_obtained=13,
        first_name="Jane",
        last_name="Austen",
        scanned_on=datetime(2017, 12, 4, 12, 12, 10, tzinfo=timezone(timedelta(hours=11))),
    )


@pytest.mark.parametrize(
    ("xml", "err", "field"),
    [
        (
            "<mcq-test-result><test-id>1</test-id>"
            "<summary-marks available='1' obtained='1'/></mcq-test-result>",
            "cardinality_violation",
            "student-number",
        ),
        (
            "<mcq-test-result><student-number>1</student-number>"
            "<student-number>1</student-number><test-id>1</test-id>"
            "<summary-marks available='1' obtained='1'/></mcq-test-result>",
            "cardinality_violation",
            "student-number",
        ),
        (
            "<mcq-test-result><student-number>   </student-number><test-id>1</test-id>"
            "<summary-marks available='1' obtained='1'/></mcq-test-result>",
            "invalid_field_value",
            "student-number",
        ),
    ],
)
def test_required_field_failures(xml: str, err: str, field: str):
    with pytest.raises(MarkrHTTPException) as ei:
        validate_record(parse(xml))
    assert ei.value.status_code == 422
    assert ei.value.error == err
    assert ei.value.details.get("field") == field


@pytest.mark.parametrize(
    ("available", "obtained"),
    [
        ("0", "0"),
        ("-3", "1"),
        ("10", "11"),
        ("twenty", "1"),
        ("10", "1.5"),
    ],
)
def test_invalid_score_cases(available: str, obtained: str):
    xml = (
        "<mcq-test-result><student-number>1</student-number><test-id>1</test-id>"
        f"<summary-marks available='{available}' obtained='{obtained}'/></mcq-test-result>"
    )
    with pytest.raises(MarkrHTTPException) as ei:
        validate_record(parse(xml))
    assert ei.value.error == "invalid_score"


def test_scanned_on_unparseable_becomes_none():
    xml = (
        "<mcq-test-result scanned-on='not-a-date'>"
        "<student-number>1</student-number><test-id>1</test-id>"
        "<summary-marks available='10' obtained='5'/></mcq-test-result>"
    )
    assert validate_record(parse(xml)).scanned_on is None


def test_scanned_on_empty_string_becomes_none():
    xml = (
        "<mcq-test-result scanned-on=''>"
        "<student-number>1</student-number><test-id>1</test-id>"
        "<summary-marks available='10' obtained='5'/></mcq-test-result>"
    )
    assert validate_record(parse(xml)).scanned_on is None


def test_empty_optional_first_name_becomes_none():
    xml = (
        "<mcq-test-result><first-name></first-name>"
        "<student-number>1</student-number><test-id>1</test-id>"
        "<summary-marks available='10' obtained='5'/></mcq-test-result>"
    )
    assert validate_record(parse(xml)).first_name is None


def test_unknown_and_answer_elements_ignored():
    xml = (
        "<mcq-test-result><answer>foo</answer><reporting-team-junk/>"
        "<student-number>1</student-number><test-id>1</test-id>"
        "<summary-marks available='10' obtained='5'/></mcq-test-result>"
    )
    assert validate_record(parse(xml)).marks_obtained == 5


def test_long_test_id_rejected():
    long_test_id = "x" * 257
    xml = (
        f"<mcq-test-result><student-number>1</student-number><test-id>{long_test_id}</test-id>"
        "<summary-marks available='1' obtained='1'/></mcq-test-result>"
    )
    with pytest.raises(MarkrHTTPException) as ei:
        validate_record(parse(xml))
    assert ei.value.error == "invalid_field_value"


def test_duplicate_summary_marks_rejected():
    xml = (
        "<mcq-test-result><student-number>1</student-number><test-id>1</test-id>"
        "<summary-marks available='1' obtained='1'/>"
        "<summary-marks available='1' obtained='1'/></mcq-test-result>"
    )
    with pytest.raises(MarkrHTTPException) as ei:
        validate_record(parse(xml))
    assert ei.value.error == "cardinality_violation"
    assert ei.value.details.get("field") == "summary-marks"


def test_optional_first_last_multiple_values_last_non_empty_wins():
    xml = (
        "<mcq-test-result><first-name>A</first-name><first-name> </first-name>"
        "<first-name>B</first-name><last-name>C</last-name><last-name>D</last-name>"
        "<student-number>1</student-number><test-id>1</test-id>"
        "<summary-marks available='10' obtained='5'/></mcq-test-result>"
    )
    r = validate_record(parse(xml))
    assert r.first_name == "B"
    assert r.last_name == "D"


def test_element_order_independence_summary_marks_can_be_last():
    xml = (
        "<mcq-test-result scanned-on='2017-12-04T12:12:10+11:00'>"
        "<test-id>1234</test-id><last-name>Austen</last-name>"
        "<student-number>521585128</student-number><first-name>Jane</first-name>"
        "<answer question='1'>A</answer>"
        "<summary-marks available='20' obtained='13'/></mcq-test-result>"
    )
    assert validate_record(parse(xml)).marks_obtained == 13
